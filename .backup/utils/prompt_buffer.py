import os
import json

DATAS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "datas")
BUFFER_FILE = os.path.join(DATAS_DIR, "prompt_buffer.json")


class PromptBuffer:
    """워크플로우 간 프롬프트를 전달하기 위한 버퍼 노드.
    프롬프트를 파일에 저장하고, 저장된 파일을 읽어 출력한다."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "positive": ("STRING", {"forceInput": True}),
                "negative": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("positive", "negative")
    FUNCTION = "func"
    CATEGORY = "🐴GHTools/Utils"
    OUTPUT_NODE = True

    def func(self, positive=None, negative=None):
        os.makedirs(DATAS_DIR, exist_ok=True)

        # 입력이 하나라도 있으면 파일에 저장
        if positive is not None or negative is not None:
            data = {
                "positive": positive if positive is not None else "",
                "negative": negative if negative is not None else "",
            }
            with open(BUFFER_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        # 저장된 파일에서 읽기
        if os.path.isfile(BUFFER_FILE):
            with open(BUFFER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            out_positive = data.get("positive", "")
            out_negative = data.get("negative", "")
        else:
            out_positive = ""
            out_negative = ""

        return (out_positive, out_negative)
