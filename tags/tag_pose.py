from .tag_loader import TagNodeBase


class TagPoseNode(TagNodeBase):
    _category = "pose"

    @classmethod
    def INPUT_TYPES(cls):
        def dropdown(keys):
            return ["none"] + list(keys)

        keywords = cls._load_keywords()
        return {
            "required": {
                "stand": (
                    dropdown(keywords["TAG_STAND"].keys()),
                    {"default": "none"},
                ),
                "lying": (
                    dropdown(keywords["TAG_LYING"].keys()),
                    {"default": "none"},
                ),
                "sitting": (
                    dropdown(keywords["TAG_SITTING"].keys()),
                    {"default": "none"},
                ),
                "arm1": (
                    dropdown(keywords["TAG_ARM"].keys()),
                    {"default": "none"},
                ),
                "arm2": (
                    dropdown(keywords["TAG_ARM"].keys()),
                    {"default": "none"},
                ),
                "leg1": (
                    dropdown(keywords["TAG_LEG"].keys()),
                    {"default": "none"},
                ),
                "leg2": (
                    dropdown(keywords["TAG_LEG"].keys()),
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

    def build_keywords(self, stand, lying, sitting, arm1, arm2, leg1, leg2, text):
        parts = []

        def add_from(mapping, key):
            value = mapping.get(key)
            if value:
                parts.append(value)

        for mapping, key in (
            (self.TAG_STAND, stand),
            (self.TAG_LYING, lying),
            (self.TAG_SITTING, sitting),
            (self.TAG_ARM, arm1),
            (self.TAG_ARM, arm2),
            (self.TAG_LEG, leg1),
            (self.TAG_LEG, leg2),
        ):
            if key != "none":
                add_from(mapping, key)

        manual = (text or "").strip()
        if manual:
            parts.append(manual)

        combined = " ".join(p.strip() for p in parts) if parts else ""

        return (combined,)
