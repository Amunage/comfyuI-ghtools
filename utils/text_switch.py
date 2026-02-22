class TextSwitch:
    """
    스위치가 있는 텍스트 입력 노드.
    ON/OFF 스위치와 텍스트 입력칸으로 구성.
    스위치가 ON(True)이면 텍스트 출력, OFF(False)이면 빈 문자열 출력.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "switch": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "label_on": "ON",
                        "label_off": "OFF",
                    },
                ),
                "text": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "placeholder": "text",
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "func"
    CATEGORY = "GHTools/Utils"

    def func(self, switch: bool, text: str):
        if switch:
            return (text + "\n",)
        else:
            return ("",)
