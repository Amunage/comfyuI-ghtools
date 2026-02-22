class TagHandNode:
    TAG_HANDUPPER = {
        "안경 위치를 고쳐잡음": "adjusting eyewear,",
        "귀를 기울임": "hand mouth,",
        "안경에 손을 올림": "hand on eyewear,",
        "모자를 만잠": "hand on headwear,",
        "자신의 뺨을 만짐": "hand on own cheek,",
        "자신의 턱을 만짐": "hand on own chin,",
        "자신의 귀를 만짐": "hand on own ear,",
        "자신의 얼굴을 만짐": " hand on own face,",
        "자신의 이마에 손을 올림": "hand on own forehead,",
        "자신의 이마를 붙잡음": "Hand on own head,",
        "자신의 목을 붙잡음": "hand on own neck,",
        "자신의 어깨에 손을 올림": "hand on own shoulder,",
        "자신의 동물귀를 붙잡고 아래로 내림": "pulling own ear,",
        "자신/타인의 얼굴을 누르거나 당김": "cheek squas,",
    }

    TAG_HANDUPPER2 = {
        "타인의 머리카락을 만짐": "adjusting another's hair,",
        "어깨동무": "arm around shoulder,",
        "타인의 볼을 당기기": "cheek pinching,",
        "타인의 볼을 찌르기": "cheek poking,",
        "타인의 목을 조름": "strangling,",
        "타인의 뺨을 어루만짐": "hand on another's cheek,",
        "타인의 턱을 잡음": "hand on another's chin,",
        "타인의 귀를 만짐": "hand on another's ear,",
        "타인의 얼굴을 만짐": "hand on another's face,",
        "타인의 목을 잡음": "hand on another's neck,",
        "타인의 어깨를 잡음": "hand on another's shoulder,",
        "타인의 머리를 쓰다듬음": "headpat,",
    }

    TAG_HANDCHEST1 = {
        "자신의 팔을 잡음": "hand on own arm,",
        "자신의 팔꿈치를 잡음": "hand on own elbow,",
        "자신의 양팔을 잡음": "hands on own arms,",
        "손에 머리를 얹고 쉬는 자세": "head rest,",
        "팔을 V자로 모아 가슴을 압박함": "v arms,",
    } 

    TAG_HANDCHEST2 = {
        "타인의 팔을 만짐": "hand on another's arm,",
        "타인의 등 뒤로 팔을 뻗음": "hand on another's back,",
        "타인의 배를 만짐": "hand on another's stomach,",
    } 

    TAG_HANDBREAST1 = {
        "팔을 가슴 아래로 걸침": "arm under breasts,",
        "양팔을 가슴 아래로 걸침": "arms under breasts,",
        "가슴을 들어올림": "breast lift,",
        "가슴을 누르는 행위": "breast poke,",
        "한손/양손을 가슴 위에 올림": "breast suppress,",
        "손/팔로 가슴을 압박": "breasts squeezed together,",
        "빈유의 가슴 만지기": "flat chest grab,",
        "자신의 가슴을 움켜쥠": "grabbing own breast,",
        "브라에 손을 올림": "hand in bra,",
        "가슴 위에 손을 올림": "hand on own chest,",
        "꼭지 잡고 돌리거나 비틀기": "nipple tweak,",

    }

    TAG_HANDBREAST2 = {
        "타인의 가슴을 움켜쥠": "grabbing another's breast,",
        "타인을 더듬거나 만지거나 찌름": "groping,",
        "타인이 가슴을 만지게함": "guided breast grab,",
        "타인의 가슴에 손이 있음": "hand on another's chest,",
    }

    TAG_HANDLOWER = {
        "손을 다리 사이에 둠": "hand between legs,",
        "손을 자신의 엉덩이에 둠": "hand on own ass,",
        "손을 자신의 사타구니에 둠": "hand on own crotch,",
        "양손을 다리 사이에 둠": "hands between legs,",
        "양손을 자신의 엉덩이에 둠": "hands on own ass,",
        "양손을 자신의 사타구니에 둠": "hands on own crotch,",
        "손을 자신의 발에 둠": "hand on own foot,",
        "손을 자신의 골반에 올림": "hand on own hip,",
        "손을 자신의 무릎에 올림": "hand on own knee,",
        "양손을 자신의 발에 둠": "hands on own feet,",
        "양손을 자신의 골반에 올림": "hands on own hips,",
        "양손을 자신의 무릎에 올림": "hands on own knees,",
        "손을 자신의 다리에 둠": "hand on own leg,",
        "손을 자신의 배에 올림": "hand on own stomach,",
        "손을 자신의 허벅지에 올림": "hand on own thigh,",
        "양손을 자신의 다리에 둠": "hands on own legs,",
        "양손을 자신의 배에 올림": "hands on own stomach,",
        "양손을 자신의 허벅지에 올림": "hands on own thighs,",
        "손을 자신의 주머니에 넣음": "hand in pocket,",
        "양손을 자신의 주머니에 넣음": "hands in pockets,"
    }

    TAG_HANDLOWER2 = {
        "타인의 엉덩이에 손을 올림": "hand on another's ass,",
        "타인의 사타구니에 손을 올림": "hand on another's crotch,",
        "타인의 엉덩이에 양손을 올림": "hands on another's ass,",
        "타인의 사타구니에 양손을 올림": "hands on another's crotch,",
        "타인의 허벅지에 손을 올림": "hand on another's thigh,",
        "타인의 허리에 손을 올림": "hand on another's waist,",
        "타인의 허벅지에 양손을 올림": "hands on another's thighs,",
        "타인의 허리에 양손을 올림": "hands on another's waist,",
        "타인의 골반에 손을 올림": "hand on another's hip,",
        "타인의 무릎에 손을 올림": "hand on another's knee,",
        "타인의 다리에 손을 올림": "hand on another's leg,",
        "타인의 몸통을 붙잡음": "torso grab,",
    }

    @classmethod
    def INPUT_TYPES(cls):
        def dropdown(keys):
            return ["none"] + list(keys)

        return {
            "required": {
                "upper_self": (
                    dropdown(cls.TAG_HANDUPPER.keys()),
                    {"default": "none"},
                ),
                "upper_other": (
                    dropdown(cls.TAG_HANDUPPER2.keys()),
                    {"default": "none"},
                ),
                "chest_self": (
                    dropdown(cls.TAG_HANDCHEST1.keys()),
                    {"default": "none"},
                ),
                "chest_other": (
                    dropdown(cls.TAG_HANDCHEST2.keys()),
                    {"default": "none"},
                ),
                "breast_self": (
                    dropdown(cls.TAG_HANDBREAST1.keys()),
                    {"default": "none"},
                ),
                "breast_other": (
                    dropdown(cls.TAG_HANDBREAST2.keys()),
                    {"default": "none"},
                ),
                "lower_self": (
                    dropdown(cls.TAG_HANDLOWER.keys()),
                    {"default": "none"},
                ),
                "lower_other": (
                    dropdown(cls.TAG_HANDLOWER2.keys()),
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
        upper_self,
        upper_other,
        chest_self,
        chest_other,
        breast_self,
        breast_other,
        lower_self,
        lower_other,
        text,
    ):
        parts = []

        for mapping, key in (
            (self.TAG_HANDUPPER, upper_self),
            (self.TAG_HANDUPPER2, upper_other),
            (self.TAG_HANDCHEST1, chest_self),
            (self.TAG_HANDCHEST2, chest_other),
            (self.TAG_HANDBREAST1, breast_self),
            (self.TAG_HANDBREAST2, breast_other),
            (self.TAG_HANDLOWER, lower_self),
            (self.TAG_HANDLOWER2, lower_other),
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

