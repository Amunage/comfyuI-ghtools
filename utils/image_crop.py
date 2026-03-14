import time
from threading import Event

import torch
import torch.nn.functional as F
from nodes import PreviewImage
from server import PromptServer
from aiohttp import web
from comfy import model_management as mm


class ImageCropSelectionCancelled(Exception):
    pass


def _get_crop_cache():
    if not hasattr(PromptServer.instance, '_ghtools_image_crop_selection'):
        PromptServer.instance._ghtools_image_crop_selection = {}
    return PromptServer.instance._ghtools_image_crop_selection


def _cleanup_session(node_id):
    cache = _get_crop_cache()
    if node_id in cache:
        for key in ("event", "crop", "cancelled"):
            cache[node_id].pop(key, None)


def _wait_for_crop(node_id, period=0.1):
    try:
        node_id = str(node_id)
        cache = _get_crop_cache()

        cache.pop(node_id, None)
        event = Event()
        cache[node_id] = {
            "event": event,
            "crop": None,
            "cancelled": False,
        }

        try:
            PromptServer.instance.send_sync("ghtools-image-crop-waiting", {
                "id": node_id,
            })
        except Exception:
            pass

        while node_id in cache:
            mm.throw_exception_if_processing_interrupted()
            info = cache[node_id]

            if info.get("cancelled", False):
                _cleanup_session(node_id)
                raise ImageCropSelectionCancelled("Crop cancelled")

            if info.get("crop") is not None:
                break

            time.sleep(period)

        if node_id in cache:
            crop = cache[node_id].get("crop")
            _cleanup_session(node_id)
            return crop

        return None

    except ImageCropSelectionCancelled:
        raise mm.InterruptProcessingException()
    except mm.InterruptProcessingException:
        cache = _get_crop_cache()
        if str(node_id) in cache:
            _cleanup_session(str(node_id))
        raise
    except Exception:
        cache = _get_crop_cache()
        if str(node_id) in cache:
            _cleanup_session(str(node_id))
        return None


def _do_crop(image, crop):
    x = max(0, int(crop["x"]))
    y = max(0, int(crop["y"]))
    w = max(1, int(crop["width"]))
    h = max(1, int(crop["height"]))

    _, img_h, img_w, _ = image.shape
    x = min(x, img_w - 1)
    y = min(y, img_h - 1)
    w = min(w, img_w - x)
    h = min(h, img_h - y)

    return image[:, y:y + h, x:x + w, :]


def _restore_size(cropped, orig_h, orig_w):
    # (batch, H, W, C) -> (batch, C, H, W) for F.interpolate
    x = cropped.permute(0, 3, 1, 2)
    x = F.interpolate(x, size=(orig_h, orig_w), mode="bilinear", align_corners=False)
    return x.permute(0, 2, 3, 1)


class ImageCrop(PreviewImage):

    NAME = "GH Image Crop"
    CATEGORY = "GHTools/Utils"
    FUNCTION = "crop_image"
    DESCRIPTION = "Preview an image and interactively crop a region by mouse drag."

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, image, mode="Always Select", restore_original_size=False,
                   unique_id=None, prompt=None, extra_pnginfo=None):
        if mode == "Always Select":
            return float("nan")
        return ""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "mode": (["Always Select", "Always Pass", "Keep Last Area"],),
                "restore_original_size": ("BOOLEAN", {"default": False}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    def crop_image(self, image, mode="Always Select", restore_original_size=False,
                   unique_id=None, filename_prefix="gh.crop.", prompt=None, extra_pnginfo=None):
        saved = self.save_images(image, filename_prefix, prompt, extra_pnginfo)
        result = {"ui": {"images": saved["ui"]["images"]}}
        _, orig_h, orig_w, _ = image.shape

        # Always Pass — bypass
        if mode == "Always Pass":
            result["result"] = (image,)
            return result

        # Keep Last Area — reuse cached crop without waiting
        if mode == "Keep Last Area":
            cache = _get_crop_cache()
            node_id = str(unique_id)
            if node_id in cache and "last_crop" in cache[node_id]:
                crop = cache[node_id]["last_crop"]
                cropped = _do_crop(image, crop)
                if restore_original_size:
                    cropped = _restore_size(cropped, orig_h, orig_w)
                result["result"] = (cropped,)
            else:
                # no last crop yet — fall through to interactive
                try:
                    PromptServer.instance.send_sync("ghtools-image-crop-keep-selection", {
                        "id": node_id,
                    })
                except Exception:
                    pass
                result["result"] = (image,)
            return result

        # Always Select — interactive
        try:
            PromptServer.instance.send_sync("ghtools-image-crop-images", {
                "id": str(unique_id),
                "images": saved["ui"]["images"],
            })
        except Exception:
            pass

        crop = _wait_for_crop(unique_id)

        if crop is None:
            result["result"] = (image,)
            return result

        # Save last crop for "Keep Last Area"
        cache = _get_crop_cache()
        node_id = str(unique_id)
        if node_id not in cache:
            cache[node_id] = {}
        cache[node_id]["last_crop"] = crop

        cropped = _do_crop(image, crop)
        if restore_original_size:
            cropped = _restore_size(cropped, orig_h, orig_w)
        result["result"] = (cropped,)
        return result


@PromptServer.instance.routes.post('/ghtools/image_crop_message')
async def handle_image_crop_message(request):
    try:
        data = await request.json()
        node_id = str(data.get("node_id"))
        action = data.get("action")

        cache = _get_crop_cache()
        if node_id not in cache:
            return web.json_response({"code": -1, "error": "Node data does not exist"})

        info = cache[node_id]

        if action == "cancel":
            info["cancelled"] = True
            info["crop"] = None
        elif action == "crop":
            crop_data = data.get("crop")
            if not crop_data:
                return web.json_response({"code": -1, "error": "Missing crop data"})
            info["crop"] = {
                "x": float(crop_data["x"]),
                "y": float(crop_data["y"]),
                "width": float(crop_data["width"]),
                "height": float(crop_data["height"]),
            }
            info["cancelled"] = False
        else:
            return web.json_response({"code": -1, "error": "Invalid action"})

        if "event" in info:
            info["event"].set()

        return web.json_response({"code": 1})

    except Exception:
        return web.json_response({"code": -1, "message": "Request Failed"})
