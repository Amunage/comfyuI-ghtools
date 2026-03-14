"""
Video Preview Node - VideoCombine 래퍼: 미리보기 후 저장/패스/재시도 선택
VHS(Video Helper Suite)의 VideoCombine을 직접 호출하여 인코딩 로직 중복 제거
"""
import os
import re
import shutil
import time
from threading import Event

import torch
import folder_paths
from server import PromptServer
from aiohttp import web
from comfy import model_management as mm

# ─── VHS 동적 import ──────────────────────────────────────────────
_vhs_loaded = False
_VideoCombine = None
_get_video_formats = None
_imageOrLatent = "IMAGE"
_floatOrInt = "FLOAT"
_ContainsAll = None


class _FallbackContainsAll(dict):
    """VHS 로드 실패 시 사용할 폴백"""
    def __init__(self, base_dict=None):
        super().__init__(base_dict or {})
    def __contains__(self, item):
        return True
    def __getitem__(self, key):
        if key in self.keys():
            return super().__getitem__(key)
        return None


def _ensure_vhs():
    """VHS 모듈을 한 번만 로드 (게으른 초기화)"""
    global _vhs_loaded, _VideoCombine, _get_video_formats
    global _imageOrLatent, _floatOrInt, _ContainsAll
    import sys

    if _vhs_loaded:
        return _VideoCombine is not None

    _vhs_loaded = True

    # 방법 1: 직접 import
    try:
        from comfyui_videohelpersuite.videohelpersuite.nodes import (
            VideoCombine, get_video_formats,
        )
        from comfyui_videohelpersuite.videohelpersuite.utils import (
            imageOrLatent, floatOrInt, ContainsAll,
        )
        _VideoCombine = VideoCombine
        _get_video_formats = get_video_formats
        _imageOrLatent = imageOrLatent
        _floatOrInt = floatOrInt
        _ContainsAll = ContainsAll
        return True
    except Exception:
        pass

    # 방법 2: sys.modules에서 이미 로드된 VHS 찾기
    for name, module in sys.modules.items():
        if module is None or not getattr(module, '__file__', None):
            continue
        if 'videohelpersuite' not in (module.__file__ or '').lower():
            continue
        if name.endswith('.nodes'):
            _VideoCombine = getattr(module, 'VideoCombine', _VideoCombine)
            _get_video_formats = getattr(module, 'get_video_formats', _get_video_formats)
        if name.endswith('.utils'):
            _imageOrLatent = getattr(module, 'imageOrLatent', _imageOrLatent)
            _floatOrInt = getattr(module, 'floatOrInt', _floatOrInt)
            _ContainsAll = getattr(module, 'ContainsAll', _ContainsAll)

    return _VideoCombine is not None


# ─── 미리보기 세션 관리 ───────────────────────────────────────────

class VideoPreviewCancelled(Exception):
    pass


def _cache():
    if not hasattr(PromptServer.instance, '_ghtools_video_preview'):
        PromptServer.instance._ghtools_video_preview = {}
    return PromptServer.instance._ghtools_video_preview


def _cleanup(node_id):
    data = _cache()
    if node_id in data:
        for k in ("event", "action", "cancelled"):
            data[node_id].pop(k, None)


def wait_for_video_action(node_id, preview_info, period=0.1):
    """미리보기를 표시하고 사용자 액션(Save/Pass/Retry)을 대기"""
    try:
        node_id = str(node_id)
        data = _cache()

        if node_id in data:
            _cleanup(node_id)
        else:
            data[node_id] = {}

        event = Event()
        data[node_id].update({
            "event": event,
            "action": None,
            "cancelled": False,
            "preview_info": preview_info,
        })

        try:
            PromptServer.instance.send_sync("ghtools-video-preview-waiting", {
                "id": node_id, "preview": preview_info,
            })
        except Exception:
            pass

        while node_id in data:
            mm.throw_exception_if_processing_interrupted()
            info = data[node_id]
            if info.get("cancelled"):
                _cleanup(node_id)
                raise VideoPreviewCancelled()
            if info.get("action") is not None:
                break
            time.sleep(period)

        if node_id in data:
            action = data[node_id].get("action")
            data[node_id]["last_action"] = action
            _cleanup(node_id)
            return action
        return None

    except VideoPreviewCancelled:
        raise mm.InterruptProcessingException()
    except mm.InterruptProcessingException:
        _cleanup(str(node_id))
        raise
    except Exception:
        _cleanup(str(node_id) if not isinstance(node_id, str) else node_id)
        raise


# ─── VideoPreview 노드 ───────────────────────────────────────────

class VideoPreview:
    """
    VHS VideoCombine 래퍼 — 미리보기 후 Save / Pass / Retry 선택
    인코딩은 VHS에 위임하고, 이 노드는 UI 제어만 담당한다.
    """

    @classmethod
    def INPUT_TYPES(cls):
        _ensure_vhs()
        if _get_video_formats is not None:
            ffmpeg_formats, format_widgets = _get_video_formats()
        else:
            ffmpeg_formats, format_widgets = [], {}
        format_widgets["image/webp"] = [['lossless', "BOOLEAN", {'default': True}]]

        CA = _ContainsAll or _FallbackContainsAll
        iorl = _imageOrLatent or "IMAGE"
        foi = _floatOrInt or "FLOAT"

        return {
            "required": {
                "images": (iorl,),
                "frame_rate": (foi, {"default": 8, "min": 1, "step": 1}),
                "loop_count": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1}),
                "filename_prefix": ("STRING", {"default": "VideoPreview"}),
                "format": (["image/gif", "image/webp"] + ffmpeg_formats,
                           {'formats': format_widgets}),
                "pingpong": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "audio": ("AUDIO",),
                "meta_batch": ("VHS_BatchManager",),
                "vae": ("VAE",),
            },
            "hidden": CA({
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID",
            }),
        }

    RETURN_TYPES = ("VHS_FILENAMES", "IMAGE")
    RETURN_NAMES = ("Filenames", "images")
    OUTPUT_NODE = True
    FUNCTION = "execute"
    CATEGORY = "🐴GHTools/Utils"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    # ── 핵심 실행 ────────────────────────────────────────────────

    def execute(
        self,
        frame_rate,
        loop_count,
        images=None,
        latents=None,
        filename_prefix="VideoPreview",
        format="image/gif",
        pingpong=False,
        prompt=None,
        extra_pnginfo=None,
        audio=None,
        unique_id=None,
        manual_format_widgets=None,
        meta_batch=None,
        vae=None,
        **kwargs,
    ):
        # 이미지 유효성 체크
        if latents is not None:
            images = latents
        if images is None:
            return ((False, []), images)
        if isinstance(images, torch.Tensor) and images.size(0) == 0:
            return ((False, []), images)

        # 원본 보존 (Pass 출력용)
        original_images = images.clone() if isinstance(images, torch.Tensor) else images

        # VHS 로드 확인
        if not _ensure_vhs() or _VideoCombine is None:
            raise RuntimeError(
                "VideoPreview 노드는 VHS(Video Helper Suite)가 필요합니다.\n"
                "ComfyUI Manager에서 'ComfyUI-VideoHelperSuite'를 설치해 주세요."
            )

        # ── 1단계: VHS VideoCombine으로 임시 인코딩 ──
        combiner = _VideoCombine()
        vhs_result = combiner.combine_video(
            images=images,
            frame_rate=frame_rate,
            loop_count=loop_count,
            filename_prefix=filename_prefix,
            format=format,
            pingpong=pingpong,
            save_output=False,          # temp 디렉토리에 저장
            prompt=prompt,
            extra_pnginfo=extra_pnginfo,
            audio=audio,
            unique_id=unique_id,
            manual_format_widgets=manual_format_widgets,
            meta_batch=meta_batch,
            vae=vae,
            **kwargs,
        )

        # VHS 반환값 파싱
        preview_info = vhs_result["ui"]["gifs"][0]
        vhs_filenames = vhs_result["result"][0]  # (save_output, [file_paths])
        preview_info["type"] = "temp"

        # ── 2단계: 미리보기 표시 + 사용자 액션 대기 ──
        action = wait_for_video_action(str(unique_id), preview_info)

        # ── 3단계: 액션별 처리 ──
        if action == "save":
            return self._handle_save(
                vhs_filenames, preview_info, filename_prefix,
                format, frame_rate, unique_id, original_images,
            )
        elif action == "retry":
            self._send_event("ghtools-video-preview-retry", unique_id)
            raise mm.InterruptProcessingException()
        else:
            # "pass" 또는 기본
            self._send_event("ghtools-video-preview-passed", unique_id)
            return {"ui": {"gifs": [preview_info]},
                    "result": ((False, []), original_images)}

    # ── Save 처리 ────────────────────────────────────────────────

    def _handle_save(self, vhs_filenames, preview_info, filename_prefix,
                     fmt, frame_rate, unique_id, original_images):
        output_dir = folder_paths.get_output_directory()
        (final_folder, final_name, _, final_sub, _) = \
            folder_paths.get_save_image_path(filename_prefix, output_dir)

        # 카운터 계산
        max_c = 0
        matcher = re.compile(
            rf"{re.escape(final_name)}_(\d+)\D*\..+", re.IGNORECASE)
        for f in os.listdir(final_folder):
            m = matcher.fullmatch(f)
            if m:
                max_c = max(max_c, int(m.group(1)))
        counter = max_c + 1

        # temp → output 복사
        saved = []
        temp_files = vhs_filenames[1] if len(vhs_filenames) > 1 else []
        for temp_file in temp_files:
            if not os.path.exists(temp_file):
                continue
            ext = os.path.splitext(temp_file)[1]
            base = os.path.basename(temp_file)
            if "-audio" in base:
                new_name = f"{final_name}_{counter:05}-audio{ext}"
            elif base.endswith(".png"):
                new_name = f"{final_name}_{counter:05}.png"
            else:
                new_name = f"{final_name}_{counter:05}{ext}"
            dst = os.path.join(final_folder, new_name)
            shutil.copy2(temp_file, dst)
            saved.append(dst)

        result_info = {
            "filename": os.path.basename(saved[-1]) if saved else "",
            "subfolder": final_sub,
            "type": "output",
            "format": fmt,
            "frame_rate": frame_rate,
        }
        self._send_event("ghtools-video-preview-saved", unique_id, result_info)
        return {"ui": {"gifs": [result_info]},
                "result": ((True, saved), original_images)}

    # ── 유틸 ─────────────────────────────────────────────────────

    @staticmethod
    def _send_event(event_name, unique_id, extra=None):
        try:
            payload = {"id": str(unique_id)}
            if extra:
                payload["result"] = extra
            PromptServer.instance.send_sync(event_name, payload)
        except Exception:
            pass


# ─── API 라우트 ───────────────────────────────────────────────────

@PromptServer.instance.routes.post('/ghtools/video_preview_action')
async def handle_video_preview_action(request):
    try:
        body = await request.json()
        node_id = str(body.get("node_id"))
        action = body.get("action")  # "save", "pass", "retry", "cancel"

        data = _cache()
        if node_id not in data:
            return web.json_response({"code": -1, "error": "Node data does not exist"})

        info = data[node_id]
        if action == "cancel":
            info["cancelled"] = True
            info["action"] = None
        elif action in ("save", "pass", "retry"):
            info["action"] = action
            info["cancelled"] = False
        else:
            return web.json_response({"code": -1, "error": "Invalid action"})

        if "event" in info:
            info["event"].set()
        return web.json_response({"code": 1})

    except Exception:
        return web.json_response({"code": -1, "message": "Request Failed"})
