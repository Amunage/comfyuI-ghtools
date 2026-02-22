class TagAgeNode:
    TAG_AGE = {
        "아기": "baby,",
        "유아기": "toddler,",
        "아동기": "child,",
        "청소년기": "adolescent,",
        "성인": "young adult,",
        "노인": "old,",
    }

    TAG_AGESCALE = {
        "어려짐": "aged down,",
        "나이듬": "aged up,",
        "성숙함": "mature female,",
        "로리": "loli,",
        "어린아이": "belly,",
    }

    @classmethod
    def INPUT_TYPES(cls):
        dropdown_age = ["none"] + list(cls.TAG_AGE.keys())
        dropdown_scale = ["none"] + list(cls.TAG_AGESCALE.keys())
        return {
            "required": {
                "age": (
                    dropdown_age,
                    {"default": "none"},
                ),
                "age_scale": (
                    dropdown_scale,
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

    def build_keywords(self, age, age_scale, text):
        parts = []

        if age != "none":
            value = self.TAG_AGE.get(age)
            if value:
                parts.append(value)

        if age_scale != "none":
            value = self.TAG_AGESCALE.get(age_scale)
            if value:
                parts.append(value)

        manual = (text or "").strip()
        if manual:
            parts.append(manual)

        combined = " ".join(p.strip() for p in parts) if parts else ""

        return (combined,)

