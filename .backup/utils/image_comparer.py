from threading import Event
import time

from nodes import PreviewImage
from server import PromptServer
from aiohttp import web
from comfy import model_management as mm


class ImageComparerSelectionCancelled(Exception):
  pass


def get_image_comparer_cache():
  if not hasattr(PromptServer.instance, '_ghtools_image_comparer_selection'):
    PromptServer.instance._ghtools_image_comparer_selection = {}
  return PromptServer.instance._ghtools_image_comparer_selection


def cleanup_session_data(node_id):
  node_data = get_image_comparer_cache()
  if node_id in node_data:
    session_keys = ["event", "selected", "cancelled", "retry"]
    for key in session_keys:
      if key in node_data[node_id]:
        del node_data[node_id][key]


def _resolve_selected_image(selected, image_a, image_b):
  if selected == "A" and image_a is not None and len(image_a) > 0:
    return image_a
  if selected == "B" and image_b is not None and len(image_b) > 0:
    return image_b
  if image_a is not None and len(image_a) > 0:
    return image_a
  if image_b is not None and len(image_b) > 0:
    return image_b
  return image_a


def wait_for_image_comparer_selection(node_id, image_a, image_b, mode, period=0.1):
  try:
    node_id = str(node_id)
    node_data = get_image_comparer_cache()

    if mode == "Always Select A":
      return _resolve_selected_image("A", image_a, image_b)
    if mode == "Always Select B":
      return _resolve_selected_image("B", image_a, image_b)
    if mode == "Keep Last Selection":
      if node_id in node_data and "last_selection" in node_data[node_id]:
        last_selection = node_data[node_id]["last_selection"]
        try:
          PromptServer.instance.send_sync("ghtools-image-comparer-keep-selection", {
            "id": node_id,
            "selected": last_selection,
          })
        except Exception:
          pass
        cleanup_session_data(node_id)
        return _resolve_selected_image(last_selection, image_a, image_b)

    if node_id in node_data:
      del node_data[node_id]

    event = Event()
    node_data[node_id] = {
      "event": event,
      "selected": None,
      "cancelled": False,
      "retry": False,
    }

    try:
      PromptServer.instance.send_sync("ghtools-image-comparer-waiting", {
        "id": node_id,
      })
    except Exception:
      pass

    while node_id in node_data:
      mm.throw_exception_if_processing_interrupted()

      node_info = node_data[node_id]

      if node_info.get("cancelled", False):
        cleanup_session_data(node_id)
        raise ImageComparerSelectionCancelled("Image comparer selection cancelled")

      if node_info.get("retry", False):
        try:
          PromptServer.instance.send_sync("ghtools-image-comparer-retry", {
            "id": node_id,
          })
        except Exception:
          pass
        cleanup_session_data(node_id)
        raise ImageComparerSelectionCancelled("Image comparer selection retry")

      if node_info.get("selected") is not None:
        break

      time.sleep(period)

    if node_id in node_data:
      node_info = node_data[node_id]
      selected = node_info.get("selected")
      node_data[node_id]["last_selection"] = selected
      cleanup_session_data(node_id)
      return _resolve_selected_image(selected, image_a, image_b)

    return _resolve_selected_image("A", image_a, image_b)

  except ImageComparerSelectionCancelled:
    raise mm.InterruptProcessingException()
  except mm.InterruptProcessingException:
    node_data = get_image_comparer_cache()
    if str(node_id) in node_data:
      cleanup_session_data(str(node_id))
    raise
  except Exception:
    node_data = get_image_comparer_cache()
    if str(node_id) in node_data:
      cleanup_session_data(str(node_id))
    return _resolve_selected_image("A", image_a, image_b)


class ImageComparer(PreviewImage):
  """A node that compares two images in the UI."""

  NAME = 'GH Image Comparer'
  CATEGORY = '🐴GHTools/Utils'
  FUNCTION = "compare_images"
  DESCRIPTION = "Compares two images with a hover slider, or click from properties."
  
  RETURN_TYPES = ("IMAGE",)
  RETURN_NAMES = ("image",)
  OUTPUT_NODE = True

  @classmethod
  def IS_CHANGED(cls, mode, image_a=None, image_b=None, unique_id=None, prompt=None, extra_pnginfo=None):
    if mode == "Always Select":
      return float("nan")
    return ""

  @classmethod
  def INPUT_TYPES(cls):  # pylint: disable = invalid-name, missing-function-docstring
    return {
      "required": {
        "mode": (["Always Select", "Always Select A", "Always Select B", "Keep Last Selection"],),
      },
      "optional": {
        "image_a": ("IMAGE",),
        "image_b": ("IMAGE",),
      },
      "hidden": {
        "unique_id": "UNIQUE_ID",
        "prompt": "PROMPT",
        "extra_pnginfo": "EXTRA_PNGINFO"
      },
    }

  def compare_images(self,
                     mode,
                     image_a=None,
                     image_b=None,
                     unique_id=None,
                     filename_prefix="gh.compare.",
                     prompt=None,
                     extra_pnginfo=None):

    result = { "ui": { "a_images":[], "b_images": [] } }
    if image_a is not None and len(image_a) > 0:
      result['ui']['a_images'] = self.save_images(image_a, filename_prefix, prompt, extra_pnginfo)['ui']['images']

    if image_b is not None and len(image_b) > 0:
      result['ui']['b_images'] = self.save_images(image_b, filename_prefix, prompt, extra_pnginfo)['ui']['images']

    try:
      PromptServer.instance.send_sync("ghtools-image-comparer-images", {
        "id": str(unique_id),
        "a_images": result['ui']['a_images'],
        "b_images": result['ui']['b_images'],
      })
    except Exception:
      pass

    selected_image = wait_for_image_comparer_selection(unique_id, image_a, image_b, mode)
    result["result"] = (selected_image,)
    return result


@PromptServer.instance.routes.post('/ghtools/image_comparer_message')
async def handle_image_comparer_selection(request):
  try:
    data = await request.json()
    node_id = str(data.get("node_id"))
    action = data.get("action")

    node_data = get_image_comparer_cache()
    if node_id not in node_data:
      return web.json_response({"code": -1, "error": "Node data does not exist"})

    node_info = node_data[node_id]
    if action == "retry":
      node_info["retry"] = True
      node_info["cancelled"] = False
      node_info["selected"] = None
    elif action == "cancel":
      node_info["cancelled"] = True
      node_info["retry"] = False
      node_info["selected"] = None
    elif action in ["A", "B"]:
      node_info["selected"] = action
      node_info["retry"] = False
      node_info["cancelled"] = False
    else:
      return web.json_response({"code": -1, "error": "Invalid action"})

    if "event" in node_info:
      node_info["event"].set()

    return web.json_response({"code": 1})

  except Exception:
    return web.json_response({"code": -1, "message": "Request Failed"})