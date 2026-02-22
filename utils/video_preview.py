"""
Video Preview Node - VideoCombine 노드 기반 비디오 미리보기 후 저장/패스/재시도 선택
VHS(Video Helper Suite)의 VideoCombine 노드를 기반으로 하여 미리보기 기능 추가
"""
import os
import sys
import json
import subprocess
import re
import datetime
import time
import itertools
import shutil
import importlib.util
from threading import Event

import numpy as np
import torch
from PIL import Image, ExifTags
from PIL.PngImagePlugin import PngInfo

import folder_paths
from server import PromptServer
from aiohttp import web
from comfy import model_management as mm
from comfy.utils import ProgressBar

# 기본값 설정
VHS_AVAILABLE = False
ffmpeg_path = None
gifski_path = None
imageOrLatent = "IMAGE"
floatOrInt = "FLOAT"
ENCODE_ARGS = ("utf-8", "backslashreplace")
BIGMAX = (2**53-1)

class ContainsAll(dict):
    """모든 키를 포함하는 것처럼 동작하는 dict - 동적 위젯용"""
    def __init__(self, base_dict=None):
        super().__init__(base_dict or {})
    
    def __contains__(self, item):
        return True
    
    def __getitem__(self, key):
        # 실제 키가 있으면 반환, 없으면 None 반환 (동적 위젯용)
        if key in self.keys():
            return super().__getitem__(key)
        return None

# ffmpeg 경로 찾기
def find_ffmpeg():
    # 환경변수에서 먼저 확인
    path = os.environ.get("VHS_FORCE_FFMPEG_PATH")
    if path and os.path.isfile(path):
        return path
    
    # imageio_ffmpeg 시도
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        path = get_ffmpeg_exe()
        if path and os.path.isfile(path):
            return path
    except:
        pass
    
    # 시스템 PATH에서 찾기
    path = shutil.which("ffmpeg")
    if path:
        return path
    
    return None

# gifski 경로 찾기
def find_gifski():
    path = os.environ.get("VHS_GIFSKI", None)
    if path and os.path.isfile(path):
        return path
    path = os.environ.get("JOV_GIFSKI", None)
    if path and os.path.isfile(path):
        return path
    path = shutil.which("gifski")
    return path

ffmpeg_path = find_ffmpeg()
gifski_path = find_gifski()

# VHS 모듈 동적 로드 시도 (sys.modules 또는 직접 경로)
def try_import_vhs():
    global VHS_AVAILABLE, imageOrLatent, floatOrInt, ContainsAll, BIGMAX, ENCODE_ARGS
    
    # 방법 1: sys.modules에서 이미 로드된 VHS 모듈 찾기
    vhs_utils = None
    vhs_nodes = None
    
    for name, module in sys.modules.items():
        if module is None:
            continue
        if hasattr(module, '__file__') and module.__file__:
            if 'videohelpersuite' in module.__file__.lower():
                if name.endswith('.utils') or 'utils' in name:
                    vhs_utils = module
                elif name.endswith('.nodes') or 'nodes' in name:
                    vhs_nodes = module
    
    # 방법 2: 직접 경로로 import 시도
    if vhs_utils is None or vhs_nodes is None:
        vhs_path = os.path.join(folder_paths.get_folder_paths("custom_nodes")[0], "ComfyUI-VideoHelperSuite")
        if not os.path.exists(vhs_path):
            # 다른 이름으로 시도
            for name in os.listdir(folder_paths.get_folder_paths("custom_nodes")[0]):
                if 'videohelpersuite' in name.lower() or 'vhs' in name.lower():
                    test_path = os.path.join(folder_paths.get_folder_paths("custom_nodes")[0], name)
                    if os.path.isdir(test_path) and os.path.exists(os.path.join(test_path, "videohelpersuite")):
                        vhs_path = test_path
                        break
        
        vhs_module_path = os.path.join(vhs_path, "videohelpersuite")
        
        if os.path.exists(vhs_module_path):
            try:
                # utils 로드
                utils_path = os.path.join(vhs_module_path, "utils.py")
                if os.path.exists(utils_path):
                    spec = importlib.util.spec_from_file_location("vhs_utils", utils_path)
                    vhs_utils = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(vhs_utils)
                
                # nodes 로드
                nodes_path = os.path.join(vhs_module_path, "nodes.py")
                if os.path.exists(nodes_path):
                    spec = importlib.util.spec_from_file_location("vhs_nodes", nodes_path)
                    vhs_nodes = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(vhs_nodes)
            except Exception as e:
                pass  # VHS import failed silently
    
    if vhs_utils:
        try:
            imageOrLatent = getattr(vhs_utils, 'imageOrLatent', imageOrLatent)
            floatOrInt = getattr(vhs_utils, 'floatOrInt', floatOrInt)
            ContainsAll = getattr(vhs_utils, 'ContainsAll', ContainsAll)
            BIGMAX = getattr(vhs_utils, 'BIGMAX', BIGMAX)
            ENCODE_ARGS = getattr(vhs_utils, 'ENCODE_ARGS', ENCODE_ARGS)
        except:
            pass
    
    return vhs_utils, vhs_nodes

# VHS video_formats 폴더에서 직접 format 목록 읽기
def get_video_formats_direct():
    """VHS의 video_formats 폴더에서 직접 format 정보 읽기"""
    formats = []
    format_widgets = {}
    
    # VHS 경로 찾기
    custom_nodes_path = folder_paths.get_folder_paths("custom_nodes")[0]
    vhs_path = None
    
    for name in os.listdir(custom_nodes_path):
        test_path = os.path.join(custom_nodes_path, name)
        if os.path.isdir(test_path):
            formats_dir = os.path.join(test_path, "video_formats")
            if os.path.exists(formats_dir):
                vhs_path = test_path
                break
    
    if not vhs_path:
        return formats, format_widgets

    formats_dir = os.path.join(vhs_path, "video_formats")
    def flatten_list(l):
        """중첩 리스트 평탄화"""
        if not isinstance(l, list):
            return l
        result = []
        for item in l:
            if isinstance(item, list):
                result.extend(flatten_list(item))
            else:
                result.append(item)
        return result
    
    def iterate_format(video_format, for_widgets=True):
        """format JSON에서 위젯 정보 추출 - VHS와 동일한 로직"""
        widgets = []
        
        def find_widgets_in_list(lst):
            """리스트를 순회하며 위젯 정의 찾기"""
            i = 0
            while i < len(lst):
                item = lst[i]
                if isinstance(item, list) and len(item) >= 2:
                    name = item[0]
                    second = item[1]
                    
                    if isinstance(second, list):
                        # ["pix_fmt", ["yuv420p10le", "yuv420p"]] 형태 - 선택 옵션
                        options = second
                        widgets.append([name, options, {'default': options[0]}])
                    elif isinstance(second, str) and second in ["BOOLEAN", "INT", "FLOAT", "STRING"]:
                        # ["crf", "INT", {"default": 22, ...}] 형태
                        opts = item[2] if len(item) > 2 else {}
                        widgets.append([name, second, opts])
                    elif isinstance(second, dict):
                        # 조건부 선택 (키-값 매핑)
                        options = list(second.keys())
                        widgets.append([name, options, {'default': options[0]}])
                i += 1
        
        def find_widgets_in_value(value):
            """값을 검사하여 위젯 정의 찾기"""
            if isinstance(value, list):
                if len(value) >= 2:
                    first = value[0]
                    second = value[1]
                    
                    if isinstance(first, str):
                        if isinstance(second, list):
                            # ["pix_fmt", ["yuv420p10le", "yuv420p"]] 형태
                            widgets.append([first, second, {'default': second[0]}])
                            return
                        elif isinstance(second, str) and second in ["BOOLEAN", "INT", "FLOAT", "STRING"]:
                            # ["save_metadata", "BOOLEAN", {"default": true}] 형태
                            opts = value[2] if len(value) > 2 else {}
                            widgets.append([first, second, opts])
                            return
                        elif isinstance(second, dict):
                            # 조건부 선택
                            options = list(second.keys())
                            widgets.append([first, options, {'default': options[0]}])
                            return
                
                # 리스트 내부 검사 (main_pass 등)
                find_widgets_in_list(value)
        
        # 모든 키-값 쌍 검사
        for key, value in video_format.items():
            if key in ['main_pass', 'first_pass', 'audio_pass']:
                # pass 리스트 내부의 위젯 찾기
                if isinstance(value, list):
                    find_widgets_in_list(value)
            else:
                # 직접 위젯 정의인지 확인
                find_widgets_in_value(value)
        
        return widgets
    
    # video_formats 디렉토리 스캔
    for item in os.scandir(formats_dir):
        if not item.is_file() or not item.name.endswith('.json'):
            continue
        
        format_name = item.name[:-5]  # .json 제거
        
        try:
            with open(item.path, 'r', encoding='utf-8') as f:
                video_format = json.load(f)
            
            # gifski 필요한 포맷은 gifski가 없으면 스킵
            if "gifski_pass" in video_format and gifski_path is None:
                continue
            
            full_format_name = "video/" + format_name
            formats.append(full_format_name)
            
            # 위젯 추출
            widgets = iterate_format(video_format)
            if widgets:
                format_widgets[full_format_name] = widgets
                
        except Exception as e:
            pass  # Format loading failed silently
    
    return formats, format_widgets

# 함수들 정의
def get_audio(file, start_time=0, duration=0):
    return None

def hash_path(path):
    return path

def validate_path(path, allow_none=False, allow_url=True):
    return path

def requeue_workflow(requeue_required=(-1,True)):
    pass

def calculate_file_hash(filename, hash_every_n=1):
    return ""

def strip_path(path):
    return path

def try_download_video(url):
    return None

def is_url(url):
    return url.startswith("http://") or url.startswith("https://")

def merge_filter_args(args, ftype="-vf"):
    pass

def tensor_to_int(tensor, bits):
    tensor = tensor.cpu().numpy() * (2**bits-1) + 0.5
    return np.clip(tensor, 0, (2**bits-1))

def tensor_to_bytes(tensor):
    return tensor_to_int(tensor, 8).astype(np.uint8)

def tensor_to_shorts(tensor):
    return tensor_to_int(tensor, 16).astype(np.uint16)

def to_pingpong(inp):
    if not hasattr(inp, "__getitem__"):
        inp = list(inp)
    yield from inp
    for i in range(len(inp)-2, 0, -1):
        yield inp[i]

def ffmpeg_process(args, video_format, video_metadata, file_path, env):
    """FFmpeg 프로세스 - VHS와 동일한 구현"""
    res = None
    frame_data = yield
    total_frames_output = 0
    
    if video_format.get('save_metadata', 'False') != 'False':
        os.makedirs(folder_paths.get_temp_directory(), exist_ok=True)
        metadata = json.dumps(video_metadata)
        metadata_path = os.path.join(folder_paths.get_temp_directory(), "metadata.txt")
        # metadata from file should escape = ; # \ and newline
        metadata = metadata.replace("\\", "\\\\")
        metadata = metadata.replace(";", "\\;")
        metadata = metadata.replace("#", "\\#")
        metadata = metadata.replace("=", "\\=")
        metadata = metadata.replace("\n", "\\\n")
        metadata = "comment=" + metadata
        with open(metadata_path, "w") as f:
            f.write(";FFMETADATA1\n")
            f.write(metadata)
        m_args = args[:1] + ["-i", metadata_path] + args[1:] + ["-metadata", "creation_time=now"]
        with subprocess.Popen(m_args + [file_path], stderr=subprocess.PIPE,
                              stdin=subprocess.PIPE, env=env) as proc:
            try:
                while frame_data is not None:
                    proc.stdin.write(frame_data)
                    frame_data = yield
                    total_frames_output += 1
                proc.stdin.flush()
                proc.stdin.close()
                res = proc.stderr.read()
            except BrokenPipeError as e:
                err = proc.stderr.read()
                if os.path.exists(file_path):
                    raise Exception("An error occurred in the ffmpeg subprocess:\n" \
                            + err.decode(*ENCODE_ARGS))
                print(err.decode(*ENCODE_ARGS), end="", file=sys.stderr)
                print("[GHVideoPreview] An error occurred when saving with metadata")
    
    if res != b'' or res is None:
        with subprocess.Popen(args + [file_path], stderr=subprocess.PIPE,
                              stdin=subprocess.PIPE, env=env) as proc:
            try:
                while frame_data is not None:
                    proc.stdin.write(frame_data)
                    frame_data = yield
                    total_frames_output += 1
                proc.stdin.flush()
                proc.stdin.close()
                res = proc.stderr.read()
            except BrokenPipeError as e:
                res = proc.stderr.read()
                raise Exception("An error occurred in the ffmpeg subprocess:\n" \
                        + res.decode(*ENCODE_ARGS))
    
    yield total_frames_output
    if res and len(res) > 0:
        print(res.decode(*ENCODE_ARGS), end="", file=sys.stderr)

def gifski_process(args, dimensions, frame_rate, video_format, file_path, env):
    """Gifski 프로세스 - VHS와 동일한 구현"""
    if gifski_path is None:
        raise Exception("gifski is required for this format but was not found")
    
    frame_data = yield
    with subprocess.Popen(args + video_format['main_pass'] + ['-f', 'yuv4mpegpipe', '-'],
                          stderr=subprocess.PIPE, stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, env=env) as procff:
        with subprocess.Popen([gifski_path] + video_format['gifski_pass']
                              + ['-W', f'{dimensions[0]}', '-H', f'{dimensions[1]}']
                              + ['-r', f'{frame_rate}']
                              + ['-q', '-o', file_path, '-'], stderr=subprocess.PIPE,
                              stdin=procff.stdout, stdout=subprocess.PIPE,
                              env=env) as procgs:
            try:
                while frame_data is not None:
                    procff.stdin.write(frame_data)
                    frame_data = yield
                procff.stdin.flush()
                procff.stdin.close()
                resff = procff.stderr.read()
                resgs = procgs.stderr.read()
                outgs = procgs.stdout.read()
            except BrokenPipeError as e:
                procff.stdin.close()
                resff = procff.stderr.read()
                resgs = procgs.stderr.read()
                raise Exception("An error occurred while creating gifski output\n" \
                        + "Make sure you are using gifski --version >=1.32.0\nffmpeg: " \
                        + resff.decode(*ENCODE_ARGS) + '\ngifski: ' + resgs.decode(*ENCODE_ARGS))
    
    if len(resff) > 0:
        print(resff.decode(*ENCODE_ARGS), end="", file=sys.stderr)
    if len(resgs) > 0:
        print(resgs.decode(*ENCODE_ARGS), end="", file=sys.stderr)

# video_formats 디렉토리 경로 캐시
_video_formats_dir = None

def get_video_formats_dir():
    """video_formats 디렉토리 경로 반환"""
    global _video_formats_dir
    if _video_formats_dir is not None:
        return _video_formats_dir
    
    custom_nodes_path = folder_paths.get_folder_paths("custom_nodes")[0]
    for name in os.listdir(custom_nodes_path):
        test_path = os.path.join(custom_nodes_path, name)
        if os.path.isdir(test_path):
            formats_dir = os.path.join(test_path, "video_formats")
            if os.path.exists(formats_dir):
                _video_formats_dir = formats_dir
                return _video_formats_dir
    return None

def apply_format_widgets(format_name, kwargs):
    """format JSON을 로드하고 kwargs 값으로 템플릿 치환"""
    from string import Template
    
    # format_name에서 "video/" 접두사 제거
    if format_name.startswith("video/"):
        format_name = format_name[6:]
    
    formats_dir = get_video_formats_dir()
    if not formats_dir:
        return {}
    
    format_path = os.path.join(formats_dir, format_name + ".json")
    if not os.path.exists(format_path):
        return {}
    
    try:
        with open(format_path, 'r', encoding='utf-8') as f:
            video_format = json.load(f)
    except Exception as e:
        return {}
    
    def process_list(lst, kwargs):
        """리스트 내의 템플릿 및 위젯 값 처리"""
        result = []
        i = 0
        while i < len(lst):
            item = lst[i]
            if isinstance(item, str):
                # 템플릿 치환
                try:
                    item = Template(item).safe_substitute(**kwargs)
                except:
                    pass
                result.append(item)
            elif isinstance(item, list) and len(item) >= 2:
                name = item[0]
                second = item[1]
                
                if isinstance(second, list):
                    # ["pix_fmt", ["yuv420p10le", "yuv420p"]] - 선택 옵션
                    if name in kwargs:
                        result.append(kwargs[name])
                    else:
                        result.append(second[0])  # 기본값
                elif isinstance(second, str) and second in ["BOOLEAN", "INT", "FLOAT", "STRING"]:
                    # ["crf", "INT", {...}] - 위젯 값
                    if name in kwargs:
                        val = kwargs[name]
                        # BOOLEAN은 포함 여부 결정
                        if second == "BOOLEAN":
                            if val and len(item) > 3:
                                result.append(item[3])  # true일 때 추가할 값
                        else:
                            result.append(str(val))
                    elif len(item) > 2 and isinstance(item[2], dict) and 'default' in item[2]:
                        result.append(str(item[2]['default']))
                elif isinstance(second, dict):
                    # 조건부 선택
                    if name in kwargs:
                        selected = str(kwargs[name])
                        if selected in second:
                            sub_val = second[selected]
                            if isinstance(sub_val, list):
                                result.extend(process_list(sub_val, kwargs))
                            else:
                                result.append(sub_val)
                    else:
                        # 기본값 (첫 번째 키)
                        first_key = list(second.keys())[0]
                        sub_val = second[first_key]
                        if isinstance(sub_val, list):
                            result.extend(process_list(sub_val, kwargs))
                        else:
                            result.append(sub_val)
                else:
                    result.append(item)
            else:
                result.append(item)
            i += 1
        return result
    
    # 각 pass 처리
    for key in ['main_pass', 'first_pass', 'audio_pass']:
        if key in video_format and isinstance(video_format[key], list):
            video_format[key] = process_list(video_format[key], kwargs)
    
    return video_format

# get_video_formats 함수 - 직접 구현 사용
def get_video_formats():
    return get_video_formats_direct()


class VideoPreviewCancelled(Exception):
    pass


def get_video_preview_cache():
    """비디오 미리보기 캐시 가져오기"""
    if not hasattr(PromptServer.instance, '_ghtools_video_preview'):
        PromptServer.instance._ghtools_video_preview = {}
    return PromptServer.instance._ghtools_video_preview


def cleanup_session_data(node_id):
    """세션 데이터 정리"""
    node_data = get_video_preview_cache()
    if node_id in node_data:
        session_keys = ["event", "action", "cancelled"]
        for key in session_keys:
            if key in node_data[node_id]:
                del node_data[node_id][key]


def wait_for_video_action(node_id, preview_info, period=0.1):
    """비디오 액션 대기 (Save/Pass/Retry)"""
    try:
        node_id = str(node_id)
        node_data = get_video_preview_cache()
        
        # 기존 데이터 정리
        if node_id in node_data:
            cleanup_session_data(node_id)
        else:
            node_data[node_id] = {}
        
        # 대기 상태 설정
        event = Event()
        node_data[node_id].update({
            "event": event,
            "action": None,
            "cancelled": False,
            "preview_info": preview_info,
        })
        
        # 프론트엔드에 대기 상태 알림 (미리보기 정보 포함)
        try:
            PromptServer.instance.send_sync("ghtools-video-preview-waiting", {
                "id": node_id,
                "preview": preview_info
            })
        except Exception:
            pass
        
        # 사용자 액션 대기
        while node_id in node_data:
            node_info = node_data[node_id]
            
            if node_info.get("cancelled", False):
                cleanup_session_data(node_id)
                raise VideoPreviewCancelled("Video preview cancelled")
            
            if node_info.get("action") is not None:
                break
            
            time.sleep(period)
        
        # 액션 결과 처리
        if node_id in node_data:
            node_info = node_data[node_id]
            action = node_info.get("action")
            
            # 마지막 액션 저장
            node_data[node_id]["last_action"] = action
            
            cleanup_session_data(node_id)
            
            return action
        
        return None
    
    except VideoPreviewCancelled:
        raise mm.InterruptProcessingException()
    except Exception as e:
        node_data = get_video_preview_cache()
        if node_id in node_data:
            cleanup_session_data(node_id)
        raise e


class VideoPreview:
    """
    비디오 미리보기 노드: VideoCombine 노드 기반
    비디오를 결합하여 미리보기 후 사용자 선택에 따라 처리
    - Save: 비디오 저장
    - Pass: 원본 이미지를 출력으로 전달
    - Retry: 큐 재실행
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        ffmpeg_formats, format_widgets = get_video_formats()
        format_widgets["image/webp"] = [['lossless', "BOOLEAN", {'default': True}]]
        
        all_formats = ["image/gif", "image/webp"] + ffmpeg_formats
        
        return {
            "required": {
                "images": (imageOrLatent,),
                "frame_rate": (
                    floatOrInt,
                    {"default": 8, "min": 1, "step": 1},
                ),
                "loop_count": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1}),
                "filename_prefix": ("STRING", {"default": "VideoPreview"}),
                "format": (all_formats, {'formats': format_widgets}),
                "pingpong": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "audio": ("AUDIO",),
                "meta_batch": ("VHS_BatchManager",),
                "vae": ("VAE",),
            },
            "hidden": ContainsAll({
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID"
            }),
        }
    
    RETURN_TYPES = ("VHS_FILENAMES", "IMAGE")
    RETURN_NAMES = ("Filenames", "images")
    OUTPUT_NODE = True
    FUNCTION = "execute"
    CATEGORY = "GHTools/Utils"
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # 항상 실행되도록 설정
        return float("nan")
    
    def execute(
        self,
        frame_rate: int,
        loop_count: int,
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
        **kwargs
    ):
        if latents is not None:
            images = latents
        if images is None:
            return ((False, []), images)
        if vae is not None:
            if isinstance(images, dict):
                images = images['samples']
            else:
                vae = None

        if isinstance(images, torch.Tensor) and images.size(0) == 0:
            return ((False, []), images)
        
        # 원본 이미지 텐서 저장 (나중에 출력용)
        original_images = images.clone() if isinstance(images, torch.Tensor) else images
        
        num_frames = len(images)
        pbar = ProgressBar(num_frames)
        
        if vae is not None:
            downscale_ratio = getattr(vae, "downscale_ratio", 8)
            width = images.size(-1)*downscale_ratio
            height = images.size(-2)*downscale_ratio
            frames_per_batch = (1920 * 1080 * 16) // (width * height) or 1
            
            def batched(it, n):
                while batch := tuple(itertools.islice(it, n)):
                    yield batch
            
            def batched_encode(imgs, vae_model, fpb):
                for batch in batched(iter(imgs), fpb):
                    image_batch = torch.from_numpy(np.array(batch))
                    yield from vae_model.decode(image_batch)
            
            images = batched_encode(images, vae, frames_per_batch)
            first_image = next(images)
            images = itertools.chain([first_image], images)
            while len(first_image.shape) > 3:
                first_image = first_image[0]
        else:
            first_image = images[0]
            images = iter(images)
        
        # 미리보기용 임시 디렉토리에 저장
        temp_dir = folder_paths.get_temp_directory()
        os.makedirs(temp_dir, exist_ok=True)
        
        (
            full_output_folder,
            filename,
            _,
            subfolder,
            _,
        ) = folder_paths.get_save_image_path(filename_prefix, temp_dir)
        
        output_files = []
        
        metadata = PngInfo()
        video_metadata = {}
        if prompt is not None:
            metadata.add_text("prompt", json.dumps(prompt))
            video_metadata["prompt"] = json.dumps(prompt)
        if extra_pnginfo is not None:
            for x in extra_pnginfo:
                metadata.add_text(x, json.dumps(extra_pnginfo[x]))
                video_metadata[x] = extra_pnginfo[x]
            extra_options = extra_pnginfo.get('workflow', {}).get('extra', {})
        else:
            extra_options = {}
        metadata.add_text("CreationTime", datetime.datetime.now().isoformat(" ")[:19])
        
        # 카운터 계산
        max_counter = 0
        matcher = re.compile(f"{re.escape(filename)}_(\\d+)\\D*\\..+", re.IGNORECASE)
        for existing_file in os.listdir(full_output_folder):
            match = matcher.fullmatch(existing_file)
            if match:
                file_counter = int(match.group(1))
                if file_counter > max_counter:
                    max_counter = file_counter
        counter = max_counter + 1
        
        # 첫 프레임을 PNG로 저장 (메타데이터 보존용)
        first_image_file = f"{filename}_{counter:05}.png"
        file_path = os.path.join(full_output_folder, first_image_file)
        if extra_options.get('VHS_MetadataImage', True) != False:
            Image.fromarray(tensor_to_bytes(first_image)).save(
                file_path,
                pnginfo=metadata,
                compress_level=4,
            )
        output_files.append(file_path)
        
        format_type, format_ext = format.split("/")
        file = ""
        total_frames_output = 0
        
        if format_type == "image":
            # Pillow를 사용한 이미지 포맷 (gif, webp)
            if meta_batch is not None:
                raise Exception("Pillow('image/') formats are not compatible with batched output")
            
            image_kwargs = {}
            if format_ext == "gif":
                image_kwargs['disposal'] = 2
            if format_ext == "webp":
                exif = Image.Exif()
                exif[ExifTags.IFD.Exif] = {36867: datetime.datetime.now().isoformat(" ")[:19]}
                image_kwargs['exif'] = exif
                image_kwargs['lossless'] = kwargs.get("lossless", True)
            
            file = f"{filename}_{counter:05}.{format_ext}"
            file_path = os.path.join(full_output_folder, file)
            
            if pingpong:
                images = to_pingpong(images)
            
            def frames_gen(imgs):
                for i in imgs:
                    pbar.update(1)
                    yield Image.fromarray(tensor_to_bytes(i))
            
            frames = frames_gen(images)
            next(frames).save(
                file_path,
                format=format_ext.upper(),
                save_all=True,
                append_images=frames,
                duration=round(1000 / frame_rate),
                loop=loop_count,
                compress_level=4,
                **image_kwargs
            )
            output_files.append(file_path)
        else:
            # FFmpeg를 사용한 비디오 포맷
            if ffmpeg_path is None:
                raise ProcessLookupError(
                    f"ffmpeg is required for video outputs and could not be found.\n"
                    f"In order to use video outputs, you must either:\n"
                    f"- Install imageio-ffmpeg with pip,\n"
                    f"- Place a ffmpeg executable in {os.path.abspath('')}, or\n"
                    f"- Install ffmpeg and add it to the system path."
                )
            
            if manual_format_widgets is not None:
                kwargs.update(manual_format_widgets)
            
            has_alpha = first_image.shape[-1] == 4
            kwargs["has_alpha"] = has_alpha
            video_format = apply_format_widgets(format_ext, kwargs)
            dim_alignment = video_format.get("dim_alignment", 2)
            
            if (first_image.shape[1] % dim_alignment) or (first_image.shape[0] % dim_alignment):
                to_pad = (-first_image.shape[1] % dim_alignment,
                          -first_image.shape[0] % dim_alignment)
                padding = (to_pad[0]//2, to_pad[0] - to_pad[0]//2,
                           to_pad[1]//2, to_pad[1] - to_pad[1]//2)
                padfunc = torch.nn.ReplicationPad2d(padding)
                
                def pad(image):
                    image = image.permute((2,0,1))
                    padded = padfunc(image.to(dtype=torch.float32))
                    return padded.permute((1,2,0))
                
                images = map(pad, images)
                dimensions = (-first_image.shape[1] % dim_alignment + first_image.shape[1],
                              -first_image.shape[0] % dim_alignment + first_image.shape[0])
            else:
                dimensions = (first_image.shape[1], first_image.shape[0])
            
            if pingpong:
                if meta_batch is not None:
                    raise Exception("pingpong is incompatible with batched output")
                images = to_pingpong(images)
                if num_frames > 2:
                    num_frames += num_frames - 2
                    pbar.total = num_frames
            
            if loop_count > 0:
                loop_args = ["-vf", "loop=loop=" + str(loop_count) + ":size=" + str(num_frames)]
            else:
                loop_args = []
            
            if video_format.get('input_color_depth', '8bit') == '16bit':
                images = map(tensor_to_shorts, images)
                i_pix_fmt = 'rgba64' if has_alpha else 'rgb48'
            else:
                images = map(tensor_to_bytes, images)
                i_pix_fmt = 'rgba' if has_alpha else 'rgb24'
            
            file = f"{filename}_{counter:05}.{video_format['extension']}"
            file_path = os.path.join(full_output_folder, file)
            
            bitrate_arg = []
            bitrate = video_format.get('bitrate')
            if bitrate is not None:
                bitrate_arg = ["-b:v", str(bitrate) + "M" if video_format.get('megabit') == 'True' else str(bitrate) + "K"]
            
            args = [ffmpeg_path, "-v", "error", "-f", "rawvideo", "-pix_fmt", i_pix_fmt,
                    "-color_range", "pc", "-colorspace", "rgb", "-color_primaries", "bt709",
                    "-color_trc", video_format.get("fake_trc", "iec61966-2-1"),
                    "-s", f"{dimensions[0]}x{dimensions[1]}", "-r", str(frame_rate), "-i", "-"] \
                    + loop_args
            
            images = map(lambda x: x.tobytes(), images)
            env = os.environ.copy()
            if "environment" in video_format:
                env.update(video_format["environment"])
            
            if "pre_pass" in video_format:
                if meta_batch is not None:
                    raise Exception("Formats which require a pre_pass are incompatible with Batch Manager.")
                images = [b''.join(images)]
                os.makedirs(folder_paths.get_temp_directory(), exist_ok=True)
                in_args_len = args.index("-i") + 2
                pre_pass_args = args[:in_args_len] + video_format['pre_pass']
                merge_filter_args(pre_pass_args)
                try:
                    subprocess.run(pre_pass_args, input=images[0], env=env,
                                   capture_output=True, check=True)
                except subprocess.CalledProcessError as e:
                    raise Exception("An error occurred in the ffmpeg prepass:\n" \
                            + e.stderr.decode(*ENCODE_ARGS))
            
            if "inputs_main_pass" in video_format:
                in_args_len = args.index("-i") + 2
                args = args[:in_args_len] + video_format['inputs_main_pass'] + args[in_args_len:]
            
            if 'gifski_pass' in video_format:
                output_process = gifski_process(args, dimensions, frame_rate, video_format, file_path, env)
                audio = None
            else:
                args += video_format['main_pass'] + bitrate_arg
                merge_filter_args(args)
                output_process = ffmpeg_process(args, video_format, video_metadata, file_path, env)
            
            output_process.send(None)
            
            for image in images:
                pbar.update(1)
                output_process.send(image)
                total_frames_output += 1
            
            try:
                total_frames_output = output_process.send(None)
                output_process.send(None)
            except StopIteration:
                pass
            
            output_files.append(file_path)
            
            # 오디오 처리
            a_waveform = None
            if audio is not None:
                try:
                    a_waveform = audio['waveform']
                except:
                    pass
            
            if a_waveform is not None:
                output_file_with_audio = f"{filename}_{counter:05}-audio.{video_format['extension']}"
                output_file_with_audio_path = os.path.join(full_output_folder, output_file_with_audio)
                
                if "audio_pass" not in video_format:
                    video_format["audio_pass"] = ["-c:a", "libopus"]
                
                channels = audio['waveform'].size(1)
                min_audio_dur = total_frames_output / frame_rate + 1
                
                if video_format.get('trim_to_audio', 'False') != 'False':
                    apad = []
                else:
                    apad = ["-af", "apad=whole_dur=" + str(min_audio_dur)]
                
                mux_args = [ffmpeg_path, "-v", "error", "-n", "-i", file_path,
                            "-ar", str(audio['sample_rate']), "-ac", str(channels),
                            "-f", "f32le", "-i", "-", "-c:v", "copy"] \
                            + video_format["audio_pass"] \
                            + apad + ["-shortest", output_file_with_audio_path]
                
                audio_data = audio['waveform'].squeeze(0).transpose(0,1).numpy().tobytes()
                merge_filter_args(mux_args, '-af')
                
                try:
                    res = subprocess.run(mux_args, input=audio_data,
                                         env=env, capture_output=True, check=True)
                except subprocess.CalledProcessError as e:
                    raise Exception("An error occurred in the ffmpeg subprocess:\n" \
                            + e.stderr.decode(*ENCODE_ARGS))
                if res.stderr:
                    print(res.stderr.decode(*ENCODE_ARGS), end="", file=sys.stderr)
                output_files.append(output_file_with_audio_path)
                file = output_file_with_audio
        
        # 미리보기 정보 생성
        preview_info = {
            "filename": file,
            "subfolder": subfolder,
            "type": "temp",
            "format": format,
            "frame_rate": frame_rate,
            "workflow": first_image_file,
            "fullpath": output_files[-1],
        }
        
        if num_frames == 1 and 'png' in format and '%03d' in file:
            preview_info['format'] = 'image/png'
            preview_info['filename'] = file.replace('%03d', '001')
        
        # 미리보기를 표시하고 사용자 액션 대기
        action = wait_for_video_action(str(unique_id), preview_info)
        
        if action == "save":
            # 최종 저장: output 디렉토리로 파일 복사/이동
            output_dir = folder_paths.get_output_directory()
            (
                final_output_folder,
                final_filename,
                _,
                final_subfolder,
                _,
            ) = folder_paths.get_save_image_path(filename_prefix, output_dir)
            
            # 카운터 계산
            max_counter = 0
            matcher = re.compile(f"{re.escape(final_filename)}_(\\d+)\\D*\\..+", re.IGNORECASE)
            for existing_file in os.listdir(final_output_folder):
                match = matcher.fullmatch(existing_file)
                if match:
                    file_counter = int(match.group(1))
                    if file_counter > max_counter:
                        max_counter = file_counter
            final_counter = max_counter + 1
            
            # 파일 복사
            import shutil
            saved_files = []
            for temp_file in output_files:
                if os.path.exists(temp_file):
                    ext = os.path.splitext(temp_file)[1]
                    base = os.path.basename(temp_file)
                    
                    # 파일명 재구성
                    if "-audio" in base:
                        new_filename = f"{final_filename}_{final_counter:05}-audio{ext}"
                    elif base.endswith(".png"):
                        new_filename = f"{final_filename}_{final_counter:05}.png"
                    else:
                        new_filename = f"{final_filename}_{final_counter:05}{ext}"
                    
                    final_path = os.path.join(final_output_folder, new_filename)
                    shutil.copy2(temp_file, final_path)
                    saved_files.append(final_path)
            
            result_info = {
                "filename": os.path.basename(saved_files[-1]) if saved_files else file,
                "subfolder": final_subfolder,
                "type": "output",
                "format": format,
                "frame_rate": frame_rate,
            }
            
            # 저장 완료 알림
            try:
                PromptServer.instance.send_sync("ghtools-video-preview-saved", {
                    "id": str(unique_id),
                    "result": result_info
                })
            except Exception:
                pass
            
            return {"ui": {"gifs": [result_info]}, "result": ((True, saved_files), original_images)}
        
        elif action == "pass":
            # 원본 이미지를 그대로 전달
            try:
                PromptServer.instance.send_sync("ghtools-video-preview-passed", {
                    "id": str(unique_id)
                })
            except Exception:
                pass
            
            return {"ui": {"gifs": [preview_info]}, "result": ((False, []), original_images)}
        
        elif action == "retry":
            # 재시도 - 큐 재실행 요청
            try:
                PromptServer.instance.send_sync("ghtools-video-preview-retry", {
                    "id": str(unique_id)
                })
            except Exception:
                pass
            raise mm.InterruptProcessingException()
        
        else:
            # 기본: Pass
            return {"ui": {"gifs": [preview_info]}, "result": ((False, []), original_images)}


# API 라우트 등록
@PromptServer.instance.routes.post('/ghtools/video_preview_action')
async def handle_video_preview_action(request):
    try:
        data = await request.json()
        node_id = str(data.get("node_id"))
        action = data.get("action")  # "save", "pass", "retry", "cancel"
        
        node_data = get_video_preview_cache()
        
        if node_id not in node_data:
            return web.json_response({"code": -1, "error": "Node data does not exist"})
        
        try:
            node_info = node_data[node_id]
            
            if action == "cancel":
                node_info["cancelled"] = True
                node_info["action"] = None
            elif action in ["save", "pass", "retry"]:
                node_info["action"] = action
                node_info["cancelled"] = False
            else:
                return web.json_response({"code": -1, "error": "Invalid action"})
            
            if "event" in node_info:
                node_info["event"].set()
            
            return web.json_response({"code": 1})
        
        except Exception as e:
            if node_id in node_data and "event" in node_data[node_id]:
                node_data[node_id]["event"].set()
            return web.json_response({"code": -1, "message": "Processing Failed"})
    
    except Exception as e:
        return web.json_response({"code": -1, "message": "Request Failed"})
