from .tag_loader import TagNodeBase


class TagEyeNode(TagNodeBase):
    _category = "eye"

    @classmethod
    def INPUT_TYPES(cls):
        def dropdown(keys):
            return ["none"] + list(keys)

        keywords = cls._load_keywords()
        return {
            "required": {
                "eye": (
                    dropdown(keywords["TAG_EYE"].keys()),
                    {"default": "none"},
                ),
                "eye_effect": (
                    dropdown(keywords["TAG_EYEEFFECT"].keys()),
                    {"default": "none"},
                ),
                "eye_surround": (
                    dropdown(keywords["TAG_EYESURROUND"].keys()),
                    {"default": "none"},
                ),
                "eye_shape": (
                    dropdown(keywords["TAG_EYESHAPE"].keys()),
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

    def build_keywords(self, eye, eye_effect, eye_surround, eye_shape, text):
        parts = []

        for mapping, key in (
            (self.TAG_EYE, eye),
            (self.TAG_EYEEFFECT, eye_effect),
            (self.TAG_EYESURROUND, eye_surround),
            (self.TAG_EYESHAPE, eye_shape),
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

