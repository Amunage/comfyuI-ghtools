class TagFocusNode:
    KEYWORDS = {
        "정면에서 본 모습": "straight-on,",
        "옆에서 본 모습": "side view,",
        "위에서 본 모습": "from above,",
        "아래서 본 모습": "from below,",
        "뒤에서 본 모습": "back view,",
        "밖에서 본 모습": "from outside,",
        "초상화 구도": "profile,",
        "초상화 구도": "portrait,",
        "치마 속을 들여다 봄": "upskirt,",
        "전신 위주": "full body,",
        "상반신 위주": "upper body,",
        "하반신 위주": "lower body,",
        "머리 위주": "headshot portrait,",
        "가슴부터 보임": "bust portrait,",
        "허벅지부터 보임": "cowboy shot,",
        "1인칭 시점": "pov,",
        "주인공 시점": "intersex pov,",
        "하이 앵글": "high angle,",
        "로우 앵글": "low angle,",
        "비스듬한 각도": "angled view,",
        "3/4 각도": "three-quarter view,",
        "지평선이 틀어진 각도": "dutch angle,",
        "가까이서 크게 보임": "foreshortening,",
        "깊이감 추가": "perspective,",
        "렌즈 왜곡": "fisheye,",
    }

    @classmethod
    def INPUT_TYPES(cls):
        options = ["none"] + list(cls.KEYWORDS.keys())

        return {
            "required": {
                "focus1": (
                    options,
                    {
                        "default": "none",
                    },
                ),
                "focus2": (
                    options,
                    {
                        "default": "none",
                    },
                ),
                "focus3": (
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

    def build_keywords(self, focus1, focus2, focus3, text):
        parts = []

        for focus in (focus1, focus2, focus3):
            if focus != "none" and focus in self.KEYWORDS:
                tags = self.KEYWORDS[focus]
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
