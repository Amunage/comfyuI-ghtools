class TagPoseNode:
    TAG_STAND = {
        "서있음": "standing,",
        "허리를 굽힘": "bent over,",
        "앞으로 기댐": "leaning forward,",
        "뒤로 기댐": "leaning back,",
        "옆으로 기댐": "leaning to the side,",
        "물에 떠있음": "afloat,",
        "물 속에 있음": "diving,",
        "떨어짐": "falling,",
        "어딘가에 걸려있음": "hanging,",
        "공중에 떠있음": "midair,",
        "발레하는 자세": "ballet pose,",
        "물구나무 서기": "handstand,",
        "허리를 휨": "backbend,",
        "공주님 안기": "princess carry,",
    }

    TAG_LYING = {
        "뒤로 누움": "on back,",
        "편히 누움": "reclining,",
        "널부러짐": "sprawled,",
        "엎드림": "on stomach,",
        "웅크림": "fetal position,",
        "네 발로 엎드림": "all fours,",
        "거꾸로된 자세": "upside-down,",
    }

    TAG_SITTING = {
        "앉음": "sitting,",
        "정좌": "seiza,",
        "의자에 앉음": "sitting on chair,",
        "바닥에 앉음": "sitting on floor,",
        "무릎 꿇고 앉음": "kneeling sitting,",
        "무릎을 감싸 앉음": "hugging knees,",
        "W자로 벌리고 앉음": "wariza,",
        "무릎 위에 앉음": "sitting on lap,",
        "쩍벌 자세": "butterfly sitting,",
        "쭈그려 앉음": "squatting,",
        "히어로 랜딩": "superhero landing,",
    }

    TAG_ARM = {
        "팔을 허리에 붙임": "arm at sides,",
        "팔을 뒤로 숨김": "arm behind back,",
        "팔짱": "arms crossed,",
        "팔을 쭉 뻗음": "arm outstretched,",
        "팔을 들어올림": "arm up,",
        "손을 머리 뒤로 넘김": "hand behind head,",
        "손 그림자": "shading eyes",
        "깍지 낀 손": "hands clasped,",
        "손을 주머니에 넣음": "hand in pockets,",
        "허리에 손": "hand on hip,",
        "손을 맞잡음": "hands together,",
        "경례": "salute,",
        "따봉": "thumbs up,",
        "손가락 가리킴": "finger point,",
        "손을 흔듬": "hand wave,",
        "고양이 손": "paw pose,",
        "허벅지에 손": "hand on thigh,",
        "성기에 손": "hand on pussy,",
        "가슴을 쥠": "grabbing breast,",
        "허벅지를 쥠": "grabbing thigh,",
        "성기를 벌림": "spreading pussy,",
        }
    
    TAG_LEG = {
        "다리를 벌림": "spread legs,",
        "다리를 꼼": "crossed legs,",
        "발을 다소곳이 모음": "feet together,",
        "걸터앉아 다리를 벌림": "straddling,",
        "무릎을 붙임": "knees together,",
        "무릎을 붙이고 발은 떨어짐": "knees together feet apart,",
        "무릎을 떼고 발을 붙임": "knees apart feet together,",
        "무릎을 위로 올림": "knees up,",
        "다리를 다소곳이 모음": "legs to the side,",
        "두다리를 위로 올림": "legs up,",
        "한쪽 다리만 올림": "one leg up,",
        "다리를 넓게 벌림": "wide stance,",
        "발목을 교차": "crossed ankles,",
    }

    @classmethod
    def INPUT_TYPES(cls):
        def dropdown(keys):
            return ["none"] + list(keys)

        return {
            "required": {
                "stand": (
                    dropdown(cls.TAG_STAND.keys()),
                    {"default": "none"},
                ),
                "lying": (
                    dropdown(cls.TAG_LYING.keys()),
                    {"default": "none"},
                ),
                "sitting": (
                    dropdown(cls.TAG_SITTING.keys()),
                    {"default": "none"},
                ),
                "arm1": (
                    dropdown(cls.TAG_ARM.keys()),
                    {"default": "none"},
                ),
                "arm2": (
                    dropdown(cls.TAG_ARM.keys()),
                    {"default": "none"},
                ),
                "leg1": (
                    dropdown(cls.TAG_LEG.keys()),
                    {"default": "none"},
                ),
                "leg2": (
                    dropdown(cls.TAG_LEG.keys()),
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
