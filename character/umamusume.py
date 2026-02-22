import os
import json


class Umamusume:
    _data_cache = None        # 캐릭터 JSON 캐시
    _commons_cache = None     # 공용 의상 JSON 캐시

    @classmethod
    def _load_data(cls):
        """umamusume_keywords.json에서 캐릭터 데이터를 읽어오는 함수"""
        if cls._data_cache is not None:
            return cls._data_cache

        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "umamusume_keywords.json")

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                cls._data_cache = json.load(f)
        except Exception as e:
            print(f"[Umamusume] umamusume_keywords.json 로드 실패: {e}")
            cls._data_cache = {}

        return cls._data_cache

    @classmethod
    def _load_commons(cls):
        """umamusume_commons.json에서 공용 의상 데이터를 읽어오는 함수"""
        if cls._commons_cache is not None:
            return cls._commons_cache

        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "umamusume_commons.json")

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                cls._commons_cache = json.load(f)
        except Exception as e:
            print(f"[Umamusume] umamusume_commons.json 로드 실패: {e}")
            cls._commons_cache = {}

        return cls._commons_cache

    @classmethod
    def INPUT_TYPES(cls):
        data = cls._load_data()
        commons = cls._load_commons()

        # 캐릭터 리스트: umamusume_keywords.json의 최상위 key들
        if data:
            character_list = list(data.keys())
        else:
            character_list = []

        default_character = character_list[0] if character_list else ""

        # 의상 드롭다운:
        # base (name + base),
        # naked (name + base + naked),
        # race (name + base + race),
        # casual (name + base + casual),
        # 그 뒤로 공용 의상들
        base_outfits = ["base", "naked", "race", "casual"]
        if commons:
            outfit_list = base_outfits + list(commons.keys())
        else:
            outfit_list = base_outfits

        return {
            "required": {
                "character": (
                    character_list,
                    {
                        "default": default_character
                    }
                ),
                "outfit": (
                    outfit_list,
                    {
                        "default": "base"
                    }
                ),
                "text": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": ""
                    }
                ),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("keywords",)

    FUNCTION = "get_keywords"
    CATEGORY = "GHTools/Character"

    def get_keywords(self, character, outfit, text):
        data = self._load_data()
        commons = self._load_commons()

        manual_text = (text or "").strip()

        # 캐릭터 데이터 없음 → text만 출력
        if not data or character not in data:
            return (manual_text,)

        char_data = data[character]

        # 2) 정상 outfit 처리
        name_tags = char_data.get("name", "")
        base_tags = char_data.get("base", "")

        extra_outfit_tags = ""
        common_tags = ""

        if outfit == "naked":
            extra_outfit_tags = "naked, "
        elif outfit in ("race", "casual"):
            extra_outfit_tags = char_data.get(outfit, "")
        elif commons and outfit in commons:
            common_tags = commons[outfit]
        # outfit == base → base만 출력

        # 최종 parts 조립
        parts = []

        if name_tags:
            parts.append(name_tags)
        if base_tags:
            parts.append(base_tags)
        if extra_outfit_tags:
            parts.append(extra_outfit_tags)
        if common_tags:
            parts.append(common_tags)
        if manual_text:
            parts.append(manual_text)

        if parts:
            tags = " ".join(p.strip() for p in parts)
        else:
            tags = ""

        return (tags,)
