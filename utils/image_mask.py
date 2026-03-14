import numpy as np
import torch
from PIL import Image, ImageFilter


def _feather(mask: np.ndarray, radius: float) -> np.ndarray:
    if radius <= 0:
        return mask.astype(np.float32)
    img = Image.fromarray((mask * 255.0).clip(0, 255).astype(np.uint8), mode="L")
    blur = img.filter(ImageFilter.GaussianBlur(radius=float(radius)))
    return (np.asarray(blur, dtype=np.float32) / 255.0).clip(0.0, 1.0)


def _grow_mask(mask: np.ndarray, grow_pixels: int) -> np.ndarray:
    if grow_pixels <= 0:
        return mask.astype(np.float32)
    size = int(grow_pixels) * 2 + 1
    img = Image.fromarray((mask * 255.0).clip(0, 255).astype(np.uint8), mode="L")
    grown = img.filter(ImageFilter.MaxFilter(size=size))
    return (np.asarray(grown, dtype=np.float32) / 255.0).clip(0.0, 1.0)


def _largest_connected_component(binary_mask: np.ndarray) -> np.ndarray:
    h, w = binary_mask.shape
    visited = np.zeros((h, w), dtype=bool)
    best_component = []

    for y in range(h):
        for x in range(w):
            if not binary_mask[y, x] or visited[y, x]:
                continue

            stack = [(y, x)]
            visited[y, x] = True
            component = []

            while stack:
                cy, cx = stack.pop()
                component.append((cy, cx))

                if cy > 0 and binary_mask[cy - 1, cx] and not visited[cy - 1, cx]:
                    visited[cy - 1, cx] = True
                    stack.append((cy - 1, cx))
                if cy < h - 1 and binary_mask[cy + 1, cx] and not visited[cy + 1, cx]:
                    visited[cy + 1, cx] = True
                    stack.append((cy + 1, cx))
                if cx > 0 and binary_mask[cy, cx - 1] and not visited[cy, cx - 1]:
                    visited[cy, cx - 1] = True
                    stack.append((cy, cx - 1))
                if cx < w - 1 and binary_mask[cy, cx + 1] and not visited[cy, cx + 1]:
                    visited[cy, cx + 1] = True
                    stack.append((cy, cx + 1))

            if len(component) > len(best_component):
                best_component = component

    out = np.zeros((h, w), dtype=np.float32)
    for y, x in best_component:
        out[y, x] = 1.0
    return out


def _filter_small_components(binary_mask: np.ndarray, min_region_size: int) -> np.ndarray:
    if min_region_size <= 1:
        return binary_mask.astype(np.float32)

    h, w = binary_mask.shape
    visited = np.zeros((h, w), dtype=bool)
    out = np.zeros((h, w), dtype=np.float32)

    for y in range(h):
        for x in range(w):
            if not binary_mask[y, x] or visited[y, x]:
                continue

            stack = [(y, x)]
            visited[y, x] = True
            component = []

            while stack:
                cy, cx = stack.pop()
                component.append((cy, cx))

                if cy > 0 and binary_mask[cy - 1, cx] and not visited[cy - 1, cx]:
                    visited[cy - 1, cx] = True
                    stack.append((cy - 1, cx))
                if cy < h - 1 and binary_mask[cy + 1, cx] and not visited[cy + 1, cx]:
                    visited[cy + 1, cx] = True
                    stack.append((cy + 1, cx))
                if cx > 0 and binary_mask[cy, cx - 1] and not visited[cy, cx - 1]:
                    visited[cy, cx - 1] = True
                    stack.append((cy, cx - 1))
                if cx < w - 1 and binary_mask[cy, cx + 1] and not visited[cy, cx + 1]:
                    visited[cy, cx + 1] = True
                    stack.append((cy, cx + 1))

            if len(component) >= int(min_region_size):
                for py, px in component:
                    out[py, px] = 1.0

    return out


class ImageMask:
    """
    Build a mask from target RGBA and tolerance settings.
    - Outputs 3-channel image (RGB)
    - Outputs mask (selected area = 1.0)
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "red": ("INT", {"default": 0, "min": 0, "max": 255, "step": 1}),
                "green": ("INT", {"default": 0, "min": 0, "max": 255, "step": 1}),
                "blue": ("INT", {"default": 0, "min": 0, "max": 255, "step": 1}),
                "alpha": ("INT", {"default": 255, "min": 0, "max": 255, "step": 1}),
                "threshold": ("FLOAT", {"default": 0.98, "min": 0.0, "max": 1.0, "step": 0.01}),
                "min_region_size": ("INT", {"default": 50, "min": 0, "max": 1048576, "step": 1}),
                "mask_grow": ("INT", {"default": 0, "min": 0, "max": 256, "step": 1}),
                "feather": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 128.0, "step": 0.5}),
                "connected_only": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "mask")
    FUNCTION = "make_mask"
    CATEGORY = "🐴GHTools/Utils"

    def make_mask(self, image, red, green, blue, alpha, threshold, min_region_size, mask_grow, feather, connected_only):
        if not isinstance(image, torch.Tensor):
            raise ValueError("image must be a torch.Tensor")

        if image.ndim == 3:
            image = image.unsqueeze(0)

        if image.ndim != 4:
            raise ValueError("image must have shape [B,H,W,C] or [H,W,C]")

        img = image.detach().cpu().float().clamp(0.0, 1.0)
        bsz, _, _, ch = img.shape
        if ch < 3:
            raise ValueError("image must have at least 3 channels")

        np_img = img.numpy()
        rgb = np_img[:, :, :, :3]

        if ch >= 4:
            alpha_channel = np_img[:, :, :, 3]
        else:
            alpha_channel = np.ones((bsz, np_img.shape[1], np_img.shape[2]), dtype=np.float32)

        rgb255 = rgb * 255.0
        a255 = alpha_channel * 255.0

        target_red = float(red)
        target_green = float(green)
        target_blue = float(blue)
        target_alpha = float(alpha)

        # RGB distance normalized to 0..255
        rgb_dist = np.sqrt(
            (
                (rgb255[:, :, :, 0] - target_red) ** 2
                + (rgb255[:, :, :, 1] - target_green) ** 2
                + (rgb255[:, :, :, 2] - target_blue) ** 2
            )
            / 3.0
        )
        alpha_dist = np.abs(a255 - target_alpha)

        # If image has no alpha channel, rely on RGB only.
        # If target alpha is near 0, prioritize alpha distance so 0,0,0,0 can select transparent regions
        # even when transparent pixels carry non-black RGB values.
        if ch < 4:
            combined_dist = rgb_dist
        elif target_alpha <= 8.0:
            combined_dist = alpha_dist
        else:
            combined_dist = np.maximum(rgb_dist, alpha_dist)

        strength = 1.0 - (combined_dist / 255.0)
        strength = np.clip(strength, 0.0, 1.0)

        binary = (strength >= float(threshold)).astype(np.float32)

        masks = []
        for i in range(bsz):
            base = binary[i]
            base = _filter_small_components(base > 0.5, int(min_region_size))
            if bool(connected_only):
                base = _largest_connected_component(base > 0.5)
            base = _grow_mask(base, int(mask_grow))
            masks.append(_feather(base, float(feather)))

        mask_np = np.stack(masks, axis=0).astype(np.float32)
        mask_tensor = torch.from_numpy(mask_np)

        # Always output 3-channel image.
        image_tensor = torch.from_numpy(rgb.astype(np.float32))
        return (image_tensor, mask_tensor)
