from threading import Event
import time

from server import PromptServer
from aiohttp import web
from comfy import model_management as mm
from comfy_execution.graph import ExecutionBlocker


class AnySelectionCancelled(Exception):
    pass


# ComfyUI 타입 시스템을 우회하기 위한 AnyType 클래스
class AnyType(str):
    """모든 타입과 매칭되는 특수 타입"""
    def __eq__(self, __value: object) -> bool:
        return True

    def __ne__(self, __value: object) -> bool:
        return False

# 싱글톤 인스턴스
ANY_TYPE = AnyType("*")


def get_any_selection_cache():
    """Any 선택기 캐시 가져오기"""
    if not hasattr(PromptServer.instance, '_ghtools_any_selection'):
        PromptServer.instance._ghtools_any_selection = {}
    return PromptServer.instance._ghtools_any_selection


def cleanup_session_data(node_id):
    """세션 데이터 정리"""
    node_data = get_any_selection_cache()
    if node_id in node_data:
        session_keys = ["event", "selected", "cancelled"]
        for key in session_keys:
            if key in node_data[node_id]:
                del node_data[node_id][key]


def wait_for_any_selection(node_id, input_a, input_b, mode, period=0.1):
    """Any 선택 대기"""
    try:
        # node_id를 문자열로 통일 (프론트엔드와 일치시키기 위해)
        node_id = str(node_id)
        node_data = get_any_selection_cache()
        
        # 모드에 따른 처리
        if mode == "Always Select A":
            return {"result": (input_a,)}
        elif mode == "Always Select B":
            return {"result": (input_b,)}
        elif mode == "Keep Last Selection":
            if node_id in node_data and "last_selection" in node_data[node_id]:
                last_selection = node_data[node_id]["last_selection"]
                if last_selection == "A":
                    try:
                        PromptServer.instance.send_sync("ghtools-any-keep-selection", {
                            "id": node_id,
                            "selected": "A"
                        })
                    except Exception:
                        pass
                    cleanup_session_data(node_id)
                    return {"result": (input_a,)}
                elif last_selection == "B":
                    try:
                        PromptServer.instance.send_sync("ghtools-any-keep-selection", {
                            "id": node_id,
                            "selected": "B"
                        })
                    except Exception:
                        pass
                    cleanup_session_data(node_id)
                    return {"result": (input_b,)}
        
        # 기존 데이터 정리
        if node_id in node_data:
            del node_data[node_id]
        
        # 대기 상태 설정
        event = Event()
        node_data[node_id] = {
            "event": event,
            "selected": None,
            "cancelled": False,
        }
        
        # 프론트엔드에 대기 상태 알림
        try:
            PromptServer.instance.send_sync("ghtools-any-waiting", {
                "id": node_id
            })
        except Exception:
            pass
        
        # 사용자 선택 대기
        while node_id in node_data:
            node_info = node_data[node_id]
            
            if node_info.get("cancelled", False):
                cleanup_session_data(node_id)
                raise AnySelectionCancelled("Any selection cancelled")
            
            if node_info.get("retry", False):
                # 재실행: 프론트엔드에 재큐잉 요청 후 중단
                try:
                    PromptServer.instance.send_sync("ghtools-any-retry", {
                        "id": node_id
                    })
                except Exception:
                    pass
                cleanup_session_data(node_id)
                raise AnySelectionCancelled("Any selection retry")
            
            if node_info.get("selected") is not None:
                break
            
            time.sleep(period)
        
        # 선택 결과 처리
        if node_id in node_data:
            node_info = node_data[node_id]
            selected = node_info.get("selected")
            
            # 마지막 선택 저장
            if node_id not in node_data:
                node_data[node_id] = {}
            node_data[node_id]["last_selection"] = selected
            
            cleanup_session_data(node_id)
            
            if selected == "A":
                return {"result": (input_a,)}
            elif selected == "B":
                return {"result": (input_b,)}
        
        # 기본값: A 선택
        return {"result": (input_a,)}
    
    except AnySelectionCancelled:
        raise mm.InterruptProcessingException()
    except Exception as e:
        node_data = get_any_selection_cache()
        if node_id in node_data:
            cleanup_session_data(node_id)
        return {"result": (input_a,)}


class AnySelection:
    """
    Any 선택 노드: 두 개의 입력 중 하나를 선택하여 출력
    사용자가 버튼을 누르거나 모드 설정에 따라 선택 결정
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_A": (ANY_TYPE,),
                "input_B": (ANY_TYPE,),
                "mode": (["Always Select", "Always Select A", "Always Select B", "Keep Last Selection"],),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            }
        }
    
    RETURN_TYPES = (ANY_TYPE,)
    RETURN_NAMES = ("output",)
    FUNCTION = "execute"
    CATEGORY = "GHTools/Utils"
    
    @classmethod
    def IS_CHANGED(cls, input_A, input_B, mode, unique_id):
        # "Always Select" 모드일 때는 항상 캐시 무효화
        if mode == "Always Select":
            return float("nan")  # NaN은 항상 다른 값으로 취급됨
        return ""
    
    def execute(self, input_A, input_B, mode, unique_id):
        return wait_for_any_selection(unique_id, input_A, input_B, mode)


# API 라우트 등록
@PromptServer.instance.routes.post('/ghtools/any_selection_message')
async def handle_any_selection(request):
    try:
        data = await request.json()
        node_id = str(data.get("node_id"))  # 문자열로 변환
        action = data.get("action")  # "A", "B", or "cancel"
        
        node_data = get_any_selection_cache()
        
        if node_id not in node_data:
            return web.json_response({"code": -1, "error": "Node data does not exist"})
        
        try:
            node_info = node_data[node_id]
            
            if action == "cancel":
                node_info["cancelled"] = True
                node_info["selected"] = None
            elif action == "retry":
                node_info["retry"] = True
                node_info["cancelled"] = False
            elif action in ["A", "B"]:
                node_info["selected"] = action
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
