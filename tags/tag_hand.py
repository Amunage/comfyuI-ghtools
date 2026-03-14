from .tag_loader import TagNodeBase


class TagHandNode(TagNodeBase):
    _category = "hand"

    @classmethod
    def INPUT_TYPES(cls):
        def dropdown(keys):
            return ["none"] + list(keys)

        keywords = cls._load_keywords()
        return {
            "required": {
                "upper_self": (
                    dropdown(keywords["TAG_HANDUPPER"].keys()),
                    {"default": "none"},
                ),
                "upper_other": (
                    dropdown(keywords["TAG_HANDUPPER2"].keys()),
                    {"default": "none"},
                ),
                "chest_self": (
                    dropdown(keywords["TAG_HANDCHEST1"].keys()),
                    {"default": "none"},
                ),
                "chest_other": (
                    dropdown(keywords["TAG_HANDCHEST2"].keys()),
                    {"default": "none"},
                ),
                "breast_self": (
                    dropdown(keywords["TAG_HANDBREAST1"].keys()),
                    {"default": "none"},
                ),
                "breast_other": (
                    dropdown(keywords["TAG_HANDBREAST2"].keys()),
                    {"default": "none"},
                ),
                "lower_self": (
                    dropdown(keywords["TAG_HANDLOWER"].keys()),
                    {"default": "none"},
                ),
                "lower_other": (
                    dropdown(keywords["TAG_HANDLOWER2"].keys()),
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

    def build_keywords(
        self,
        upper_self,
        upper_other,
        chest_self,
        chest_other,
        breast_self,
        breast_other,
        lower_self,
        lower_other,
        text,
    ):
        parts = []

        for mapping, key in (
            (self.TAG_HANDUPPER, upper_self),
            (self.TAG_HANDUPPER2, upper_other),
            (self.TAG_HANDCHEST1, chest_self),
            (self.TAG_HANDCHEST2, chest_other),
            (self.TAG_HANDBREAST1, breast_self),
            (self.TAG_HANDBREAST2, breast_other),
            (self.TAG_HANDLOWER, lower_self),
            (self.TAG_HANDLOWER2, lower_other),
        ):
            if key != "none":
                value = mapping.get(key)
                if value:
                    parts.append(value)

        manual = (text or "").strip()
        if manual:
            parts.append(manual)

        combined = " ".join(p.strip() for p in parts) if parts else ""

        return (combined,)

