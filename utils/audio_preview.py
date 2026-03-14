from threading import Event
import time
import io
import json
import base64
import struct
import wave

from server import PromptServer
from aiohttp import web
from comfy import model_management as mm
from comfy_execution.graph import ExecutionBlocker

import torch


class AudioPreviewCancelled(Exception):
    pass


def get_audio_preview_cache():
    """오디오 프리뷰 캐시 가져오기"""
    if not hasattr(PromptServer.instance, '_ghtools_audio_preview'):
        PromptServer.instance._ghtools_audio_preview = {}
    return PromptServer.instance._ghtools_audio_preview


def cleanup_session_data(node_id):
    """세션 데이터 정리"""
    node_data = get_audio_preview_cache()
    if node_id in node_data:
        session_keys = ["event", "action", "cancelled"]
        for key in session_keys:
            if key in node_data[node_id]:
                del node_data[node_id][key]


def audio_to_base64(waveform, sample_rate):
    """오디오를 base64로 인코딩 (WAV 포맷) - torchaudio 없이 직접 작성"""
    # waveform shape: (batch, channels, samples)
    if waveform.dim() == 3:
        waveform = waveform[0]  # 첫 번째 배치만 사용
    
    # (channels, samples) → numpy
    audio_np = waveform.cpu().float().numpy()
    num_channels = audio_np.shape[0]
    num_samples = audio_np.shape[1]
    
    # float32 → int16 변환
    audio_int16 = (audio_np.T * 32767).clip(-32768, 32767).astype("int16")
    
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')


def wait_for_audio_preview(node_id, audio, mode, period=0.1):
    """오디오 프리뷰 선택 대기"""
    try:
        node_id = str(node_id)
        node_data = get_audio_preview_cache()
        
        waveform = audio["waveform"]
        sample_rate = audio["sample_rate"]
        
        # 모드에 따른 처리
        if mode == "Always Pass":
            # Always Pass에서도 오디오 데이터를 프론트엔드에 전송 (재생용)
            try:
                audio_base64 = audio_to_base64(waveform, sample_rate)
                PromptServer.instance.send_sync("ghtools-audio-preview-passed", {
                    "id": node_id,
                    "audio_data": audio_base64,
                    "sample_rate": sample_rate
                })
            except Exception as e:
                print(f"[AudioPreview] Failed to send audio data: {e}")
            return {"result": (audio,), "ui": {"audio": []}}
        
        # 기존 데이터 정리
        if node_id in node_data:
            del node_data[node_id]
        
        # 대기 상태 설정
        event = Event()
        node_data[node_id] = {
            "event": event,
            "action": None,
            "cancelled": False,
        }
        
        # 오디오를 base64로 인코딩하여 프론트엔드에 전송
        try:
            audio_base64 = audio_to_base64(waveform, sample_rate)
            PromptServer.instance.send_sync("ghtools-audio-preview-waiting", {
                "id": node_id,
                "audio_data": audio_base64,
                "sample_rate": sample_rate
            })
        except Exception as e:
            print(f"[AudioPreview] Failed to send audio data: {e}")
        
        # 사용자 선택 대기
        while node_id in node_data:
            mm.throw_exception_if_processing_interrupted()

            node_info = node_data[node_id]
            
            if node_info.get("cancelled", False):
                cleanup_session_data(node_id)
                raise AudioPreviewCancelled("Audio preview cancelled")
            
            if node_info.get("action") is not None:
                break
            
            time.sleep(period)
        
        # 선택 결과 처리
        if node_id in node_data:
            node_info = node_data[node_id]
            action = node_info.get("action")
            
            cleanup_session_data(node_id)
            
            if action == "accept":
                # 승인: 오디오 출력
                return {"result": (audio,), "ui": {"audio": []}}
            elif action == "retry":
                # 재실행: 프론트엔드에 재큐잉 요청 후 중단
                try:
                    PromptServer.instance.send_sync("ghtools-audio-preview-retry", {
                        "id": node_id
                    })
                except Exception:
                    pass
                raise mm.InterruptProcessingException()
            elif action == "cancel":
                # 중단: 실행 블록
                raise mm.InterruptProcessingException()
        
        # 기본값: 오디오 통과
        return {"result": (audio,), "ui": {"audio": []}}
    
    except AudioPreviewCancelled:
        raise mm.InterruptProcessingException()
    except mm.InterruptProcessingException:
        node_data = get_audio_preview_cache()
        if str(node_id) in node_data:
            cleanup_session_data(str(node_id))
        raise
    except Exception as e:
        print(f"[AudioPreview] Error: {e}")
        node_data = get_audio_preview_cache()
        if node_id in node_data:
            cleanup_session_data(node_id)
        return {"result": (audio,), "ui": {"audio": []}}


class AudioPreview:
    """
    오디오 프리뷰 노드: 오디오를 미리 듣고 승인/재실행/중단 선택
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "mode": (["Always Preview", "Always Pass"],),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            }
        }
    
    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "execute"
    CATEGORY = "GHTools/Utils"
    OUTPUT_NODE = True
    
    @classmethod
    def IS_CHANGED(cls, audio, mode, unique_id):
        # "Always Preview" 모드일 때는 항상 캐시 무효화
        if mode == "Always Preview":
            return float("nan")
        return ""
    
    def execute(self, audio, mode, unique_id):
        return wait_for_audio_preview(unique_id, audio, mode)


# API 라우트 등록
@PromptServer.instance.routes.post('/ghtools/audio_preview_message')
async def handle_audio_preview(request):
    try:
        data = await request.json()
        node_id = str(data.get("node_id"))
        action = data.get("action")  # "accept", "retry", or "cancel"
        
        node_data = get_audio_preview_cache()
        
        if node_id not in node_data:
            return web.json_response({"code": -1, "error": "Node data does not exist"})
        
        try:
            node_info = node_data[node_id]
            
            if action == "cancel":
                node_info["cancelled"] = True
                node_info["action"] = "cancel"
            elif action in ["accept", "retry"]:
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
