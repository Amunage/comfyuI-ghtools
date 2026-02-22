class TagGenitalNode:
    TAG_NIPPLE = {
        "유두": "nipple,",
        "작은 유두": "small nipple,",
        "큰 유두": "large nipple,",
        "핑크 유두": "pink nipple,",
        "까만 유두": "dark nipple,",
        "돌출된 유두": "erect nipple,",
        "납작한 유두": "flat nipple,",
        "민감한 유두": "sensitive nipple,",
        "젖꼭지 링": "nipple ring,",
    }

    TAG_PUSSY = {
        "보지": "pussy,",
        "질": "vagina,",
        "요도": "urethra,",
        "사타구니": "crotch,",
        "음모": "pubic hair,",
        "면도한 보지": "shaved pussy,",
        "털수북 보지": "hairy pussy,",
        "일자 보지": "innie pussy,",
        "열린 보지": "loose pussy,",
        "통통한 보지": "plump labia,",
        "젖은 보지": "pussy juice,",
        "다리로 열린 보지": "gaping pussy,",
        "손으로 열린 보지": "spread pussy,",
    }

    TAG_LABIA = {
        "음순": "labia,",
        "대음순": "labia majora,",
        "소음순": "labia minora,",
        "큰 음순": "large labia,",
        "작은 음순": "small labia,",
        "부푼 음순": "puffy labia,",
        "까만 음순": "dark labia,",
        "핑크 음순": "pink labia,",
        "클리토리스": "clitoris,",
        "큰 클리토리스": "large clit,",
        "작은 클리토리스": "small clit,",
    }

    TAG_ASS = {
        "엉덩이": "ass ,",
        "엉덩이 골": "butt crack,",
        "항문": "anus ,",
        "닫힌 항문": "tight anus,",
        "열린 항문": "loose anus,",
        "까만 항문": "dark anus,",
        "핑크 항문": "pink anus,",
        "괄약근 조임": "puckered anus,",
        "벌어진 항문": "gaping anus,",
    }

    @classmethod
    def INPUT_TYPES(cls):
        def dropdown(keys):
            return ["none"] + list(keys)

        return {
            "required": {
                "nipple": (
                    dropdown(cls.TAG_NIPPLE.keys()),
                    {"default": "none"},
                ),
                "pussy": (
                    dropdown(cls.TAG_PUSSY.keys()),
                    {"default": "none"},
                ),
                "labia": (
                    dropdown(cls.TAG_LABIA.keys()),
                    {"default": "none"},
                ),
                "ass": (
                    dropdown(cls.TAG_ASS.keys()),
                    {"default": "none"},
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

    def build_keywords(self, nipple, pussy, labia, ass, text):
        parts = []

        def add_from(mapping, key):
            value = mapping.get(key)
            if value:
                parts.append(value)

        for mapping, key in (
            (self.TAG_NIPPLE, nipple),
            (self.TAG_PUSSY, pussy),
            (self.TAG_LABIA, labia),
            (self.TAG_ASS, ass),
        ):
            if key != "none":
                add_from(mapping, key)

        manual = (text or "").strip()
        if manual:
            parts.append(manual)

        combined = " ".join(p.strip() for p in parts) if parts else ""

        return (combined,)
