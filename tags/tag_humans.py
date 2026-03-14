from .tag_loader import TagNodeBase


class TagHumansNode(TagNodeBase):
    _category = "humans"

    @classmethod
    def INPUT_TYPES(cls):
        keywords = cls._load_keywords()
        dropdown_a = ["none"] + list(keywords["KEYWORDS_A"].keys())
        dropdown_b = ["none"] + list(keywords["KEYWORDS_B"].keys())
        return {
            "required": {
                "girl": (
                    dropdown_a,
                    {
                        "default": "none"
                    }
                ),
                "man": (
                    dropdown_b,
                    {
                        "default": "none"
                    }
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

    def build_keywords(self, girl, man, text):
        parts = []
        for option in (girl, man):
            if option != "none":
                if option in self.KEYWORDS_A:
                    parts.append(self.KEYWORDS_A[option])
                elif option in self.KEYWORDS_B:
                    parts.append(self.KEYWORDS_B[option])

        manual = (text or "").strip()
        if manual:
            parts.append(manual)

        if parts:
            combined = " ".join(p.strip() for p in parts)
        else:
            combined = ""

        return (combined,)

