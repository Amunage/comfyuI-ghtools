class TagHumansNode:
    KEYWORDS_A = {
        "1girl": "1girl,",
        "2girls": "2girls,",
        "3girls": "3girls,",
        "4girls": "4girls,",
        "5girls": "5girls,",
        "6+girls": "6+girls,",
    }

    KEYWORDS_B = {
        "1man": "1man,",
        "2mans": "2mans,",
        "3mans": "3mans,",
        "4mans": "4mans,",
        "5mans": "5mans,",
        "6+mans": "6+mans,",
    }

    @classmethod
    def INPUT_TYPES(cls):
        dropdown_a = ["none"] + list(cls.KEYWORDS_A.keys())
        dropdown_b = ["none"] + list(cls.KEYWORDS_B.keys())
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

