from .tag_loader import TagNodeBase


class TagEmotionNode(TagNodeBase):
    _category = "emotion"

    @classmethod
    def INPUT_TYPES(cls):
        dropdown = ["none"] + list(cls._load_keywords()["TAG_EMOTION"].keys())
        return {
            "required": {
                "emotion1": (
                    dropdown,
                    {"default": "none"},
                ),
                "emotion2": (
                    dropdown,
                    {"default": "none"},
                ),
                "emotion3": (
                    dropdown,
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

    def build_keywords(self, emotion1, emotion2, emotion3, text):
        parts = []

        for option in (emotion1, emotion2, emotion3):
            if option != "none":
                value = self.TAG_EMOTION.get(option)
                if value:
                    parts.append(value)

        manual = (text or "").strip()
        if manual:
            parts.append(manual)

        combined = " ".join(p.strip() for p in parts) if parts else ""

        return (combined,)

