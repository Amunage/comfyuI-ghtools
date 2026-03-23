import json
import os
import random
import re
from glob import glob

_cache = None


def _split_keyword_text(text):
    parts = []
    for chunk in re.split(r"[\n,]+", str(text or "")):
        value = chunk.strip()
        if value:
            parts.append(value)
    return parts


def _normalize_keyword(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def _merge_keyword_texts(*texts):
    merged = []
    seen = set()

    for text in texts:
        for value in _split_keyword_text(text):
            normalized = _normalize_keyword(value)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(value)

    return f"{', '.join(merged)}," if merged else ""


def load_tags_json():
    """Load and cache merged datas/tag_*.json files."""
    global _cache
    if _cache is None:
        datas_dir = os.path.join(os.path.dirname(__file__), "..", "datas")
        json_paths = sorted(glob(os.path.join(datas_dir, "tag_*.json")))
        merged = {}

        for json_path in json_paths:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                continue

            for section_name, values in data.items():
                if (
                    isinstance(values, dict)
                    and isinstance(merged.get(section_name), dict)
                ):
                    for key, value in values.items():
                        if key not in merged[section_name]:
                            merged[section_name][key] = value
                else:
                    if section_name not in merged:
                        merged[section_name] = values

        _cache = merged
    return _cache


def get_all_tag_sections():
    """Return merged top-level sections from datas/tag_*.json."""
    return load_tags_json()


def build_all_loader_options():
    options = ["none"]
    for section_name, values in get_all_tag_sections().items():
        if not isinstance(values, dict):
            continue
        options.append(f"----- {section_name} -----")
        options.extend(values.keys())
    return options


class DynamicTagOptions(dict):
    """Allow dynamic optional inputs like prefix_2, prefix_3, ..."""

    def __init__(self, prefix, options):
        super().__init__()
        self.prefix = prefix
        self.options = options

    def __contains__(self, key):
        if not key.startswith(f"{self.prefix}_"):
            return False
        suffix = key[len(self.prefix) + 1:]
        return suffix.isdigit() and int(suffix) >= 2

    def __getitem__(self, key):
        if key.startswith(f"{self.prefix}_") and key[len(self.prefix) + 1:].isdigit():
            return (self.options, {"default": "none"})
        return dict.__getitem__(self, key)


class DynamicSectionTagOptions(dict):
    """Allow dynamic optional inputs for all top-level section prefixes."""

    def __init__(self, options):
        super().__init__()
        self.options = options
        self.section_names = tuple(get_all_tag_sections().keys())

    def __contains__(self, key):
        for prefix in self.section_names:
            if not key.startswith(f"{prefix}_"):
                continue
            suffix = key[len(prefix) + 1:]
            return suffix.isdigit() and int(suffix) >= 1
        return False

    def __getitem__(self, key):
        if key in self:
            return (self.options, {"default": "none"})
        return dict.__getitem__(self, key)


def collect_dynamic_values(kwargs, prefix):
    items = []
    for key, value in kwargs.items():
        if not key.startswith(f"{prefix}_"):
            continue
        if value == "none":
            continue
        if isinstance(value, str) and value.startswith("-----") and value.endswith("-----"):
            continue
        suffix = key[len(prefix) + 1:]
        if suffix.isdigit():
            items.append((int(suffix), value))
    items.sort(key=lambda x: x[0])
    return items


def collect_loader_values(kwargs):
    items = []
    section_names = tuple(get_all_tag_sections().keys())
    for key, value in kwargs.items():
        if value == "none":
            continue
        if isinstance(value, str) and value.startswith("-----") and value.endswith("-----"):
            continue
        if key.startswith("tag_"):
            suffix = key[4:]
            if suffix.isdigit():
                items.append((int(suffix), value))
            continue
        for prefix in section_names:
            if not key.startswith(f"{prefix}_"):
                continue
            suffix = key[len(prefix) + 1:]
            if suffix.isdigit():
                items.append((int(suffix), value))
            break
    items.sort(key=lambda x: x[0])
    return items


def build_tag_loader_description():
    lines = [
        "Select tags from any top-level section in datas/tag_*.json.",
        "",
        "Usage",
        "- Enter comma-separated section names in `sections`.",
        "- Turn on `random_pick` to ignore manual dropdown choices and pick one random value per section.",
        "- Leave `sections` empty to use all top-level sections.",
        "- Example: age, grade",
        "- Then pick values from the dynamic dropdowns `tag_1`, `tag_2`, ...",
        "- You can edit existing `datas/tag_*.json` files or add new ones in the `ComfyUI\custom_nodes\comfyuI-ghtools\datas` folder.",
        "",
        "Available top-level sections",
    ]
    lines.extend(f"- {name}" for name in get_all_tag_sections().keys())
    return "\n".join(lines)


class TagLoader:
    @staticmethod
    def _parse_sections(sections, all_sections):
        selected = []
        seen = set()
        for section in str(sections or "").split(","):
            name = section.strip().lower()
            if not name or name in seen or name not in all_sections:
                continue
            seen.add(name)
            selected.append(name)
        return selected or list(all_sections.keys())

    @classmethod
    def INPUT_TYPES(cls):
        all_sections = get_all_tag_sections()
        all_options = build_all_loader_options()
        option_map = {}
        section_values = {}

        for section_name, values in all_sections.items():
            if not isinstance(values, dict):
                continue
            section_values[section_name] = list(values.keys())
            for value in values.keys():
                option_map[value] = section_name

        cls._option_map = option_map

        return {
            "required": {
                "sections": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "",
                        "placeholder": "age, grade",
                    },
                ),
                "random_pick": (
                    "BOOLEAN",
                    {
                        "default": False,
                    },
                ),
                "preview": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "",
                    },
                ),
                "tag_1": (
                    all_options,
                    {"default": "none"},
                ),
                "text": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                    },
                ),
            },
            "optional": {
                **DynamicTagOptions("tag", all_options),
                **DynamicSectionTagOptions(all_options),
            },
            "_option_map": option_map,
            "_section_values": section_values,
            "_section_tags": all_sections,
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("keywords",)

    FUNCTION = "build_keywords"
    CATEGORY = "🐴GHTools/Utils"
    DESCRIPTION = build_tag_loader_description()

    @classmethod
    def IS_CHANGED(cls, sections="", random_pick=False, preview="", text="", **kwargs):
        if random_pick:
            return float("nan")
        selected_values = tuple(value for _, value in collect_loader_values(kwargs))
        return (
            str(sections or "").strip().lower(),
            False,
            selected_values,
            str(text or "").strip(),
        )

    def build_keywords(self, sections="", random_pick=False, preview="", text="", **kwargs):
        selected_parts = []
        all_sections = get_all_tag_sections()
        option_map = getattr(self, "_option_map", {})

        if random_pick:
            for section_name in self._parse_sections(sections, all_sections):
                section = all_sections.get(section_name, {})
                if not isinstance(section, dict) or not section:
                    continue
                selected_value = random.choice(list(section.keys()))
                tag = section.get(selected_value)
                if tag:
                    selected_parts.append(tag)
        else:
            for _, selected_value in collect_loader_values(kwargs):
                section_name = option_map.get(selected_value)
                if not section_name:
                    continue
                section = all_sections.get(section_name, {})
                tag = section.get(selected_value)
                if tag:
                    selected_parts.append(tag)

        combined = _merge_keyword_texts(", ".join(selected_parts), text)
        return {"ui": {"text": [combined]}, "result": (combined,)}
