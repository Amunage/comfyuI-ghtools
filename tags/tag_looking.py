from .tag_loader import TagNodeBase


class TagLookingNode(TagNodeBase):
    _category = "looking"

    @classmethod
    def INPUT_TYPES(cls):
        options = ["none"] + list(cls._load_keywords()["KEYWORDS"].keys())
        return {
            "required": {
                "look": (
                    options,
                    {
                        "default": "none",
                    },
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

    def build_keywords(self, look, text):
        parts = []

        for look in (look,):
            if look != "none" and look in self.KEYWORDS:
                tags = self.KEYWORDS[look]
                if tags:
                    parts.append(tags)

        manual = (text or "").strip()
        if manual:
            parts.append(manual)

        if parts:
            combined = " ".join(p.strip() for p in parts)
        else:
            combined = ""

        return (combined,)
