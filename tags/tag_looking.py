class TagLookingNode:
    KEYWORDS = {
        "이쪽": "looking at viewer,",
        "정면": "looking ahead,",
        "위쪽": "looking up,",
        "아래": "looking down,",
        "옆쪽": "looking to the side,",
        "뒷쪽": "looking back,",
        "먼곳": "looking afar,",
        "바깥": "looking at outside,",
        "사물": "looking at object,",
        "동물": "looking at animal,",
        "거울": "looking at mirror,",
        "음식": "looking at food,",
        "가슴": "looking at breasts,",
        "성기": "looking at penis,",
        "손": "looking at hand,",
        "꽃": "looking at flowers,",
        "핸드폰": "looking at phone,",
    }

    @classmethod
    def INPUT_TYPES(cls):
        options = ["none"] + list(cls.KEYWORDS.keys())
        return {
            "required": {
                "look": (
                    options,
                    {
                        "default": "none",
                    },
                ),
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

    def build_keywords(self, look, text):
        parts = []

        for look in (look,):
            if look != "none" and look in self.KEYWORDS:
                tags = self.KEYWORDS[look]
                if tags:
                    parts.append(tags)

        manual = (text or "").strip()
        if manual:
            parts.append(manual)

        if parts:
            combined = " ".join(p.strip() for p in parts)
        else:
            combined = ""

        return (combined,)
