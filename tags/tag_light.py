class TagLightNode:
    TAG_LIGHTVECTOR = {
        "뒤에서 빛이 들어옴": "backlighting,",
        "옆에서 빛이 들어옴": "sidelighting,",
        "아래서 빛이 들어옴": "underlighting,",
    }

    TAG_LIGHTTIME = {
        "아침": "morning,",
        "정오": "day,",
        "일몰": "evening,",
        "밤": "night,",
    }

    TAG_LIGHTKIND = {
        "물 속에서 들어오는 빛": "caustics,",
        "구조물 틈으로 들어온 빛": "crack of light,",
        "나뭇잎 사이로 새어들어온 빛": "dappled sunlight,",
        "미약한 빛": "dim lighting,",
        "빛살 효과": "light rays,",
        "달빛": "moonlight,",
        "반사광": "refraction,",
        "스테이지 불빛": "stage lights,",
        "구조물을 통해 들어온 빛": "sunbeam,",
        "태양광": "sunlight,",
    } 

    TAG_LIGHTSHADOW = {
        "색이 있는 그림자": "colored shadow,",
        "어둠": "dark,",
        "불길한 암흑": "darkness,",
        "그늘진 모습": "shade,",
        "그림자": "shadow,",
        "나무 그림자": "tree shade,",
        "창문 그림자": "window shadow,",
    } 

    TAG_LIGHTSOURCE = {
        "촛불": "candlelight,",
        "LED등": "ceiling light,",
        "샹들리에": "chandelier,",
        "책상 램프": "desk lamp,",
        "불티/잿불": "embers,",
        "불": "fire,",
        "손전등": "flashlight,",
        "형광등": "fluorescent lamp,",
        "응원봉": "glowstick,",
        "기름 램프": "kerosene lamp,",
        "램프": "lamp,",
        "물에 띄운 등불": "lantern on liquid,",
        "랜턴": "lantern,",
        "달": "moon,",
        "네온 불빛": "neon lights,",
        "하늘로 날리는 등불": "sky lantern,",
        "태양": "sun,",
        "횃불": "torch,",
        "벽걸이 램프": "wall lamp,",
        "나무 랜턴": "wooden lantern,",
    }

    TAG_LIGHTEFFECT = {
        "총구 불꽃": "muzzle flash,",
        "욱일승천기1": "rising sun,",
        "욱일승천기2": "sunburst,",
        "스포트라이트": "spotlight,",
        "UV 라이트": "ultraviolet light,",
        "비네팅": "vignetting,",
    }

    @classmethod
    def INPUT_TYPES(cls):
        def dropdown(keys):
            return ["none"] + list(keys)

        return {
            "required": {
                "vector": (
                    dropdown(cls.TAG_LIGHTVECTOR.keys()),
                    {"default": "none"},
                ),
                "time": (
                    dropdown(cls.TAG_LIGHTTIME.keys()),
                    {"default": "none"},
                ),
                "kind": (
                    dropdown(cls.TAG_LIGHTKIND.keys()),
                    {"default": "none"},
                ),
                "shadow": (
                    dropdown(cls.TAG_LIGHTSHADOW.keys()),
                    {"default": "none"},
                ),
                "source": (
                    dropdown(cls.TAG_LIGHTSOURCE.keys()),
                    {"default": "none"},
                ),
                "effect": (
                    dropdown(cls.TAG_LIGHTEFFECT.keys()),
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

