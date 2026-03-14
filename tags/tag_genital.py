from .tag_loader import TagNodeBase


class TagGenitalNode(TagNodeBase):
    _category = "genital"

    @classmethod
    def INPUT_TYPES(cls):
        def dropdown(keys):
            return ["none"] + list(keys)

        keywords = cls._load_keywords()
        return {
            "required": {
                "nipple": (
                    dropdown(keywords["TAG_NIPPLE"].keys()),
                    {"default": "none"},
                ),
                "pussy": (
                    dropdown(keywords["TAG_PUSSY"].keys()),
                    {"default": "none"},
                ),
                "labia": (
                    dropdown(keywords["TAG_LABIA"].keys()),
                    {"default": "none"},
                ),
                "ass": (
                    dropdown(keywords["TAG_ASS"].keys()),
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
