class ConvertValue:
    """
    아무 수치(INT 또는 FLOAT)를 입력받아 INT와 FLOAT 두 가지 형태로 출력하는 노드
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("*", {}),
            }
        }

    # 출력 타입 (INT와 FLOAT 두 가지)
    RETURN_TYPES = ("INT", "FLOAT")
    # 출력 이름 (UI 포트 라벨)
    RETURN_NAMES = ("int", "float")

    # ComfyUI가 호출할 실제 함수 이름
    FUNCTION = "convert"

    # 카테고리
    CATEGORY = "🐴GHTools/Utils"

    def convert(self, value: float):
        """
        입력받은 값을 INT와 FLOAT로 변환하여 출력
        INT는 소수점 이하를 버림(truncate) 처리
        """
        int_value = int(value)
        float_value = float(value)

        return (int_value, float_value)
