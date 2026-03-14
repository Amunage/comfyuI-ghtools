from .tag_loader import TagNodeBase


class TagGradeNode(TagNodeBase):
    _category = "grade"

    @classmethod
    def INPUT_TYPES(cls):
        # 드롭다운 항목은 dict의 key들
        dropdown = list(cls._load_keywords()["KEYWORDS"].keys())
        return {
            "required": {
                "grade": (
                    dropdown,
                    {
                        "default": "일반등급"
                    }
                ),
                # 🔹 노드 아래 텍스트 영역 (추가 태그 입력용)
                "text": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                    },
                ),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("keywords",)

    FUNCTION = "build_keywords"
    CATEGORY = "GHTools/Tags"

    def build_keywords(self, grade, text):
        parts = []

        for option in (grade):
            if option != "none":
                if option in self.KEYWORDS:
                    parts.append(self.KEYWORDS[option])
        manual = (text or "").strip()

        if manual:
            parts.append(manual)

        if parts:
            combined = " ".join(p.strip() for p in parts)
        else:
            combined = ""

        return (combined,)

