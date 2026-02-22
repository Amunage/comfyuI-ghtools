class TagEyeNode:
    TAG_EYE = {
        "동글뱅이 눈": "@_@,",
        "안쪽으로 모인 눈": "cross-eyed,",
        "버튼 눈동자": "button eyes,",
        "정신나간 눈": "crazy eyes,",
        "커다란 동공": "dilated pupils,",
        "작은 동공": "sanpaku,",
        "텅빈 눈": "empty eye,",
        "동공이 여러개": "extra pupils,",
        "오드아이": "heterochromia,",
        "수평으로 된 동공": "horizontal pupils,",
        "양쪽 눈이 다른 경우": "lazy eye,",
        "기계적인 눈": "mechanical eye,",
        "동공 모양이 서로 다름": "mismatched pupils,",
        "한쪽 눈을 다침": "missing eye,",
        "그라데이션 눈": "multicolored eyes,",
        "눈을 표현하지 않음": "no eyes,",
        "동공이 없음": "no pupils,",
        "띠용 눈": "o_o,",
        "카메라렌즈 눈": "ringed eyes,",
        "아헤가오 눈": "rolling eyes,",
        "단색 원형 눈": "solid circle eyes,",
        "단색 타원 눈": "solid oval eyes,",
        "나선형 눈": "spiral-only eyes,",
        "서로 다른 크기로 뜬 눈": "uneven eyes,",
        "눈을 위로 올림": "upturned eyes,",
        "눈을 크게 뜸": "wide-eyed,",
    }

    TAG_EYEEFFECT = {
        "안광이 길게 늘어진 표현": "eye trail,",
        "불타는 눈": "flaming eyes,",
        "한쪽 눈만 발광함": "glowing eye,",
        "양쪽 눈이 발광함": "glowing eyes,",
        "고양이 눈": "slit pupils,",
        "반짝이는 눈": "sparkling eyes,",
        "하트 눈": "symbol-shaped pupils, heart-shaped eyes,",
        "다이아몬드 눈": "symbol-shaped pupils diamond-shaped pupils,",
        "꽃 모양 눈": "symbol-shaped pupils flower-shaped pupils,",
        "별 모양 눈": "symbol-shaped pupilsstar-shaped pupils,",
        "나사 모양 눈": "symbol-shaped pupils cross-shaped pupils,",
    }

    TAG_EYESURROUND = {
        "애교살": "aegyo sal,",
        "다크서클": "bags under eyes,",
        "멍듬": "bruised eye,",
        "아이라이너": "makeup, eyeliner,",
        "아이섀도우": "makeup, eyeshadow,",
        "마스카라": "makeup, mascara,",
    } 

    TAG_EYESHAPE = {
        "커다란 눈매": "big eyes,",
        "반달 눈매": "jitome,",
        "날카로운 눈매": "tsurime,",
        "순한 눈매": "tareme,",
    } 

    @classmethod
    def INPUT_TYPES(cls):
        def dropdown(keys):
            return ["none"] + list(keys)

        return {
            "required": {
                "eye": (
                    dropdown(cls.TAG_EYE.keys()),
                    {"default": "none"},
                ),
                "eye_effect": (
                    dropdown(cls.TAG_EYEEFFECT.keys()),
                    {"default": "none"},
                ),
                "eye_surround": (
                    dropdown(cls.TAG_EYESURROUND.keys()),
                    {"default": "none"},
                ),
                "eye_shape": (
                    dropdown(cls.TAG_EYESHAPE.keys()),
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

    def build_keywords(self, eye, eye_effect, eye_surround, eye_shape, text):
        parts = []

        for mapping, key in (
            (self.TAG_EYE, eye),
            (self.TAG_EYEEFFECT, eye_effect),
            (self.TAG_EYESURROUND, eye_surround),
            (self.TAG_EYESHAPE, eye_shape),
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

