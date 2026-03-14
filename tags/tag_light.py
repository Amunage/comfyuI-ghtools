from .tag_loader import TagNodeBase


class TagLightNode(TagNodeBase):
    _category = "light"

    @classmethod
    def INPUT_TYPES(cls):
        def dropdown(keys):
            return ["none"] + list(keys)

        keywords = cls._load_keywords()
        return {
            "required": {
                "vector": (
                    dropdown(keywords["TAG_LIGHTVECTOR"].keys()),
                    {"default": "none"},
                ),
                "time": (
                    dropdown(keywords["TAG_LIGHTTIME"].keys()),
                    {"default": "none"},
                ),
                "kind": (
                    dropdown(keywords["TAG_LIGHTKIND"].keys()),
                    {"default": "none"},
                ),
                "shadow": (
                    dropdown(keywords["TAG_LIGHTSHADOW"].keys()),
                    {"default": "none"},
                ),
                "source": (
                    dropdown(keywords["TAG_LIGHTSOURCE"].keys()),
                    {"default": "none"},
                ),
                "effect": (
                    dropdown(keywords["TAG_LIGHTEFFECT"].keys()),
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
        vector,
        time,
        kind,
        shadow,
        source,
        effect,
        text,
    ):
        parts = []

        for mapping, key in (
            (self.TAG_LIGHTVECTOR, vector),
            (self.TAG_LIGHTTIME, time),
            (self.TAG_LIGHTKIND, kind),
            (self.TAG_LIGHTSHADOW, shadow),
            (self.TAG_LIGHTSOURCE, source),
            (self.TAG_LIGHTEFFECT, effect),
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

