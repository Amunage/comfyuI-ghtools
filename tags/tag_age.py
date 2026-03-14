from .tag_loader import TagNodeBase


class TagAgeNode(TagNodeBase):
    _category = "age"

    @classmethod
    def INPUT_TYPES(cls):
        keywords = cls._load_keywords()
        dropdown_age = ["none"] + list(keywords["TAG_AGE"].keys())
        dropdown_scale = ["none"] + list(keywords["TAG_AGESCALE"].keys())
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

