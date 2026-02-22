import importlib


def _load_node_registry(module_name: str):
    try:
        module = importlib.import_module(module_name, package=__name__)
    except Exception:
        return {}, {}

    class_mappings = getattr(module, "NODE_CLASS_MAPPINGS", {})
    display_mappings = getattr(module, "NODE_DISPLAY_NAME_MAPPINGS", {})
    return class_mappings, display_mappings


# ComfyUI가 인식할 수 있도록 매핑 정의
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

for category_module in (".utils", ".character", ".tags"):
    class_mappings, display_mappings = _load_node_registry(category_module)
    NODE_CLASS_MAPPINGS.update(class_mappings)
    NODE_DISPLAY_NAME_MAPPINGS.update(display_mappings)

WEB_DIRECTORY = "./web"

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]
