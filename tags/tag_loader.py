import json
import os

_cache = None


def load_tags_json():
    """JSON 키워드 파일을 전역 캐시로 한 번만 로드한다."""
    global _cache
    if _cache is None:
        json_path = os.path.join(os.path.dirname(__file__), "tags_keywords.json")
        with open(json_path, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


class TagNodeBase:
    """태그 노드 공통 베이스 클래스.

    서브클래스에서 _category 를 지정하면
    JSON의 해당 카테고리 데이터를 자동으로 로드하고,
    self.TAG_XXX 형태로 접근할 수 있다.
    """

    _category = None  # 서브클래스에서 지정 (예: "pose", "body")

    @classmethod
    def _load_keywords(cls):
        data = load_tags_json()[cls._category]
        # 카테고리가 단일 딕셔너리인 경우 (focus, grade, looking 등)
        if isinstance(data, dict) and all(isinstance(v, str) for v in data.values()):
            return data
        return data

    def __getattr__(self, name):
        """self.TAG_XXX 접근 시 JSON에서 자동 조회."""
        data = load_tags_json().get(self._category, {})
        if name in data:
            return data[name]
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")
