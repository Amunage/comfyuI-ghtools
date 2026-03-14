from .tag_loader import TagNodeBase


class TagFocusNode(TagNodeBase):
    _category = "focus"

    @classmethod
    def INPUT_TYPES(cls):
        options = ["none"] + list(cls._load_keywords()["KEYWORDS"].keys())

        return {
            "required": {
                "focus1": (
                    options,
                    {
                        "default": "none",
                    },
                ),
                "focus2": (
                    options,
                    {
                        "default": "none",
                    },
                ),
                "focus3": (
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

    def build_keywords(self, focus1, focus2, focus3, text):
        parts = []

        for focus in (focus1, focus2, focus3):
            if focus != "none" and focus in self.KEYWORDS:
                tags = self.KEYWORDS[focus]
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
