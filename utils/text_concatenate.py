def _text_index(key: str) -> int:
    if not key.startswith("text"):
        return -1
    suffix = key[4:]
    suffix = suffix.lstrip("_")
    if not suffix:
        return 0
    try:
        return int(suffix)
    except ValueError:
        digits = ""
        for ch in suffix:
            if ch.isdigit():
                digits += ch
            else:
                break
        return int(digits) if digits else 0


def _sorted_text_items(kwargs):
    def sort_key(item):
        key = item[0]
        idx = _text_index(key)
        return (idx if idx >= 0 else float("inf"), key)

    return sorted(kwargs.items(), key=sort_key)


class TextConcatenate:
    """Lightweight text concatenation helper from Text Translation nodes."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "func"
    CATEGORY = "GHTools/Utils"

    def func(self, **kwargs):
        text = ""
        for key, value in _sorted_text_items(kwargs):
            if not key.startswith("text"):
                continue
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                for sub in value:
                    if sub is not None:
                        text += str(sub)
            else:
                text += str(value)
        return (text,)


class _DynamicToggleOptions(dict):
    """Offers BOOLEAN definitions for toggle_N widgets added via JS."""

    def __init__(self, prefix: str = "toggle"):
        super().__init__()
        self.prefix = prefix
        self.template = (
            "BOOLEAN",
            {
                "default": True,
                "label_on": "ON",
                "label_off": "OFF",
            },
        )

    def __contains__(self, key):
        return key.startswith(f"{self.prefix}_")

    def __getitem__(self, key):
        if key.startswith(f"{self.prefix}_"):
            return self.template
        return dict.__getitem__(self, key)


class TextConcatenateToggle:
    """Concatenate inputs while allowing per-connection toggles."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": _DynamicToggleOptions(),
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "func"
    CATEGORY = "GHTools/Utils"

    def _group_inputs(self, kwargs):
        grouped = {}
        for key, value in kwargs.items():
            if not key.startswith("text") or key.endswith("_toggle"):
                continue
            idx = _text_index(key)
            if idx < 0:
                continue
            toggle_key = f"toggle_{idx}"
            enabled = bool(kwargs.get(toggle_key, True))
            grouped[idx] = (value, enabled)
        return grouped

    def func(self, **kwargs):
        pieces = []
        grouped = self._group_inputs(kwargs)
        for idx in sorted(grouped.keys()):
            value, enabled = grouped[idx]
            if not enabled or value is None:
                continue
            if isinstance(value, (list, tuple)):
                pieces.extend(str(sub) for sub in value if sub is not None)
            else:
                pieces.append(str(value))
        return ("".join(pieces),)
