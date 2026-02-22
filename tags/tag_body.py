class TagBodyNode:
    TAG_BODYTYPE = {
        "날씬한 몸": "petite,",
        "슬렌더": "slender,",
        "포동포동한 몸": "plump,",
        "비만": "obese,",
        "탄력 있는 몸": "toned,",
        "근육질 몸": "muscular,",
        "굴곡진 몸": "curvy,",
        "풍만한 몸": "voluptuous,",
    }

    TAG_BREASTSIZE = {
        "납작한 가슴": "flat chest,",
        "작은 가슴": "small breasts,",
        "평범한 가슴": "medium breasts,",
        "큰 가슴": "large breasts,",
        "더 큰 가슴": "huge breasts,",
        "거대한 가슴": "gigantic breasts,",
        "초월적인 가슴": "hyper breasts,",
    }

    TAG_BREASTSHAPE = {
        "탱탱한 가슴": "perky breasts,",
        "살짝 늘어진 가슴": "saggy breasts,",
        "부드러운 가슴": "soft breasts,",
        "비대칭 가슴": "asymmetrical breasts,",
        "늘어진 가슴": "hanging breasts,",
    }

    TAG_WAIST = {
        "평평한 배": "flat stomach,",
        "볼록한 배": "bloated,",
        "임신한 배": "pregnant,",
        "얇은 허리": "slim waist,",
        "좁은 허리": "narrow waist,",
        }
    
    TAG_BUTT = {
        "평평한 엉덩이": "flat butt,",
        "작은 엉덩이": "small butt,",
        "큰 엉덩이": "big butt,",
        "거대한 엉덩이": "huge butt,",
        "큼직한 엉덩이": "bubble butt,",
    }

    TAG_LEGS = {
        "짧은 다리": "short legs,",
        "긴 다리": "long legs,",
        "통통한 다리": "chunky legs,",
        "탄탄한 다리": "toned legs,",
        "얇은 다리": "thin legs,",
        "근육질 다리": "calf muscles,",
        "두꺼운 종아리": "thick calves,",
        "얇은 종아리": "thin calves,",
        "X자 다리": "knock knees,",
        "아이 다리": "cankles,",
    }   

    @classmethod
    def INPUT_TYPES(cls):
        def dropdown(keys):
            return ["none"] + list(keys)

        return {
            "required": {
                "body_type": (
                    dropdown(cls.TAG_BODYTYPE.keys()),
                    {"default": "none"},
                ),
                "breast_size": (
                    dropdown(cls.TAG_BREASTSIZE.keys()),
                    {"default": "none"},
                ),
                "breast_shape": (
                    dropdown(cls.TAG_BREASTSHAPE.keys()),
                    {"default": "none"},
                ),
                "waist": (
                    dropdown(cls.TAG_WAIST.keys()),
                    {"default": "none"},
                ),
                "butt": (
                    dropdown(cls.TAG_BUTT.keys()),
                    {"default": "none"},
                ),
                "legs": (
                    dropdown(cls.TAG_LEGS.keys()),
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

    def build_keywords(self, body_type, breast_size, breast_shape, waist, butt, legs, text):
        parts = []

        def add_from(mapping, key):
            value = mapping.get(key)
            if value:
                parts.append(value)

        for mapping, key in (
            (self.TAG_BODYTYPE, body_type),
            (self.TAG_BREASTSIZE, breast_size),
            (self.TAG_BREASTSHAPE, breast_shape),
            (self.TAG_WAIST, waist),
            (self.TAG_BUTT, butt),
            (self.TAG_LEGS, legs),
        ):
            if key != "none":
                add_from(mapping, key)

        manual = (text or "").strip()
        if manual:
            parts.append(manual)

        combined = " ".join(p.strip() for p in parts) if parts else ""

        return (combined,)
