from .tag_loader import TagNodeBase


class TagBodyNode(TagNodeBase):
    _category = "body"

    @classmethod
    def INPUT_TYPES(cls):
        def dropdown(keys):
            return ["none"] + list(keys)

        keywords = cls._load_keywords()
        return {
            "required": {
                "body_type": (
                    dropdown(keywords["TAG_BODYTYPE"].keys()),
                    {"default": "none"},
                ),
                "breast_size": (
                    dropdown(keywords["TAG_BREASTSIZE"].keys()),
                    {"default": "none"},
                ),
                "breast_shape": (
                    dropdown(keywords["TAG_BREASTSHAPE"].keys()),
                    {"default": "none"},
                ),
                "waist": (
                    dropdown(keywords["TAG_WAIST"].keys()),
                    {"default": "none"},
                ),
                "butt": (
                    dropdown(keywords["TAG_BUTT"].keys()),
                    {"default": "none"},
                ),
                "legs": (
                    dropdown(keywords["TAG_LEGS"].keys()),
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

    def build_keywords(self, body_type, breast_size, breast_shape, waist, butt, legs, text):
        parts = []

        def add_from(mapping, key):
            value = mapping.get(key)
            if value:
                parts.append(value)

        for mapping, key in (
            (self.TAG_BODYTYPE, body_type),
            (self.TAG_BREASTSIZE, breast_size),
            (self.TAG_BREASTSHAPE, breast_shape),
            (self.TAG_WAIST, waist),
            (self.TAG_BUTT, butt),
            (self.TAG_LEGS, legs),
        ):
            if key != "none":
                add_from(mapping, key)

        manual = (text or "").strip()
        if manual:
            parts.append(manual)

        combined = " ".join(p.strip() for p in parts) if parts else ""

        return (combined,)
