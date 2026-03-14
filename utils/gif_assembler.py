import datetime
import json
import os
import re
import shutil
import subprocess

import numpy as np
import torch
from PIL import Image

import folder_paths
 

DEFAULT_PREVIEW_MAX_FRAMES = 0


def _to_bhwc_uint8(images: torch.Tensor) -> np.ndarray:
	if not isinstance(images, torch.Tensor):
		raise ValueError("unique_images must be a torch.Tensor")

	if images.ndim == 3:
		images = images.unsqueeze(0)

	if images.ndim != 4:
		raise ValueError("unique_images must have shape [B,H,W,C] or [H,W,C]")

	images = images.detach().cpu().float().clamp(0.0, 1.0)
	return (images.numpy() * 255.0).round().astype(np.uint8)


def _ensure_gif_filename(name: str) -> str:
	cleaned = (name or "").strip()
	if not cleaned:
		cleaned = datetime.datetime.now().strftime("gh_reassembled_%Y%m%d_%H%M%S")
	if not cleaned.lower().endswith(".gif"):
		cleaned += ".gif"
	return cleaned


def _dedupe_filepath(path: str) -> str:
	if not os.path.exists(path):
		return path

	root, ext = os.path.splitext(path)
	index = 1
	while True:
		candidate = f"{root}_{index}{ext}"
		if not os.path.exists(candidate):
			return candidate
		index += 1


class GifAssembler:
	"""
	분해자가 만든 timeline_json과 수정된 unique 이미지 배치를 이용해 GIF를 재조립.
	"""

	@classmethod
	def INPUT_TYPES(cls):
		return {
			"required": {
				"image": ("IMAGE",),
				"image_info": ("STRING", {"forceInput": True}),
				"output_prefix": ("STRING", {"default": "fixed"}),
				"loop": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
				"speed": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.1}),
				"max_colors": ("INT", {"default": 256, "min": 2, "max": 256, "step": 1}),
				"diff_threshold": ("INT", {"default": 6, "min": 0, "max": 64, "step": 1}),
				"optimize": ("BOOLEAN", {"default": True}),
				"alpha": ("BOOLEAN", {"default": False}),
				"save_output": ("BOOLEAN", {"default": True}),
			},
			"hidden": {
				"prompt": "PROMPT",
				"extra_pnginfo": "EXTRA_PNGINFO",
			}
		}

	RETURN_TYPES = ("IMAGE",)
	RETURN_NAMES = ("image",)
	FUNCTION = "assemble"
	CATEGORY = "GHTools/Utils"
	OUTPUT_NODE = True

	def assemble(
		self,
		image,
		image_info,
		output_prefix,
		loop,
		speed,
		max_colors,
		diff_threshold,
		optimize,
		alpha,
		save_output,
		prompt=None,
		extra_pnginfo=None,
	):
		try:
			timeline = json.loads(image_info)
		except Exception as exc:
			raise ValueError(f"Invalid image_info: {exc}")

		frame_to_unique = timeline.get("frame_to_unique")
		durations_ms = timeline.get("durations_ms")
		unique_count = int(timeline.get("unique_count", 0))

		if not isinstance(frame_to_unique, list) or len(frame_to_unique) == 0:
			raise ValueError("image_info.frame_to_unique must be a non-empty list")

		if not isinstance(durations_ms, list) or len(durations_ms) != len(frame_to_unique):
			raise ValueError("image_info.durations_ms length must match frame_to_unique")

		unique_np = _to_bhwc_uint8(image)
		available_unique = int(unique_np.shape[0])
		required_unique = max(unique_count, max(int(v) for v in frame_to_unique) + 1)

		if available_unique < required_unique:
			raise ValueError(
				f"image has {available_unique} frames but image_info requires {required_unique}"
			)

		speed_mult = max(0.1, float(speed))
		compressed_map = [int(v) for v in frame_to_unique]
		compressed_durations = [max(1, int(round(v / speed_mult))) for v in durations_ms]
		if bool(optimize):
			new_map = [compressed_map[0]]
			new_durations = [compressed_durations[0]]
			for i in range(1, len(compressed_map)):
				if compressed_map[i] == new_map[-1]:
					new_durations[-1] += compressed_durations[i]
				else:
					new_map.append(compressed_map[i])
					new_durations.append(compressed_durations[i])
			compressed_map = new_map
			compressed_durations = new_durations

		assembled_np = np.stack([unique_np[int(uidx)] for uidx in compressed_map], axis=0)
		assembled_tensor = torch.from_numpy(assembled_np.astype(np.float32) / 255.0)

		use_alpha = bool(alpha) and assembled_np.shape[3] >= 4
		durations = compressed_durations

		gif_frames, gif_save_opts = _build_gif_frames(assembled_np, int(max_colors), use_alpha, int(diff_threshold))

		if int(DEFAULT_PREVIEW_MAX_FRAMES) <= 0:
			preview_count = int(len(gif_frames))
		else:
			preview_count = min(int(DEFAULT_PREVIEW_MAX_FRAMES), int(len(gif_frames)))
		preview_info = _save_output_for_ui(
			frames=gif_frames[:preview_count],
			durations=durations[:preview_count],
			loop=int(loop),
			gif_save_opts=gif_save_opts,
			filename_prefix="gh.gif.assembled.preview",
		)

		gif_path = ""
		if bool(save_output):
			output_dir = folder_paths.get_output_directory()
			os.makedirs(output_dir, exist_ok=True)

			filename = _ensure_gif_filename(output_prefix)
			gif_path = _dedupe_filepath(os.path.join(output_dir, filename))

			save_kwargs = {
				"save_all": True,
				"append_images": gif_frames[1:],
				"duration": durations,
				"loop": int(loop),
			}
			save_kwargs.update(gif_save_opts)

			gif_frames[0].save(gif_path, **save_kwargs)

			# gifsicle handles both inter-frame diff and palette optimization
			# better than Pillow, especially for alpha GIFs.
			if bool(optimize):
				_run_gifsicle_optimize(gif_path, use_alpha)

		return {
			"ui": {
				"gifs": [preview_info],
			},
			"result": (assembled_tensor,),
		}


def _build_gif_frames(assembled_np: np.ndarray, max_colors: int, use_alpha: bool, diff_threshold: int = 6):
	"""Returns (frames, extra_save_kwargs) with inter-frame diff optimization."""
	if use_alpha:
		return _build_alpha_gif_frames(assembled_np, max_colors, diff_threshold)

	pil_frames = [Image.fromarray(frame[:, :, :3], mode="RGB") for frame in assembled_np]

	if len(pil_frames) <= 1:
		first_p = pil_frames[0].quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
		return [first_p], {"disposal": 2}

	# Reserve one palette slot for inter-frame transparency index.
	opaque_colors = max(2, max_colors - 1)
	trans_idx = opaque_colors

	first_p = pil_frames[0].quantize(colors=opaque_colors, method=Image.Quantize.MEDIANCUT)
	full_quantized = [first_p]
	for frame in pil_frames[1:]:
		full_quantized.append(frame.quantize(palette=first_p))

	# Inter-frame diff: mark visually unchanged pixels as transparent.
	palette = first_p.getpalette()
	pal_rgb = np.array(palette[:opaque_colors * 3], dtype=np.int16).reshape(-1, 3)
	optimized = [full_quantized[0]]
	prev_pixels = np.array(full_quantized[0], dtype=np.uint8)
	prev_rgb = assembled_np[0][:, :, :3].astype(np.int16)

	for i in range(1, len(full_quantized)):
		curr_pixels = np.array(full_quantized[i], dtype=np.uint8)
		curr_rgb = assembled_np[i][:, :, :3].astype(np.int16)
		unchanged = np.max(np.abs(curr_rgb - prev_rgb), axis=2) <= diff_threshold
		diff_pixels = curr_pixels.copy()
		diff_pixels[unchanged] = trans_idx

		new_frame = Image.fromarray(diff_pixels, mode="P")
		new_frame.putpalette(palette)
		prev_pixels = curr_pixels
		prev_rgb = curr_rgb
		optimized.append(new_frame)

	return optimized, {"transparency": trans_idx, "disposal": 1}


def _build_alpha_gif_frames(assembled_np: np.ndarray, max_colors: int, diff_threshold: int = 6):
	# Alpha GIFs are built as full frames (disposal=2) to avoid ghosting/overlap artifacts.
	# Reserve index 0 for transparency. Opaque colors occupy indices 1..N.
	usable = max(2, min(int(max_colors), 256) - 1)
	trans_idx = 0

	first_rgba = Image.fromarray(assembled_np[0][:, :, :4], mode="RGBA")
	first_rgb = first_rgba.convert("RGB")
	base_palette = first_rgb.quantize(colors=usable, method=Image.Quantize.MEDIANCUT)

	base_raw_palette = base_palette.getpalette()[:usable * 3]
	# idx 0 = transparency, 1..usable = opaque colors
	full_palette = [0, 0, 0] + base_raw_palette
	needed = (usable + 1) * 3
	if len(full_palette) < needed:
		full_palette.extend([0] * (needed - len(full_palette)))
	if len(full_palette) < 768:
		full_palette.extend([0] * (768 - len(full_palette)))

	full_indexed = []
	for frame in assembled_np:
		rgba = Image.fromarray(frame[:, :, :4], mode="RGBA")
		rgb = rgba.convert("RGB")
		quant = rgb.quantize(palette=base_palette, dither=Image.Dither.NONE)

		idx = np.array(quant, dtype=np.uint16) + 1  # shift to 1..usable
		alpha_channel = np.array(rgba.getchannel("A"), dtype=np.uint8)
		idx[alpha_channel <= 127] = trans_idx
		full_indexed.append(idx.astype(np.uint8))

	frames = []
	for idx in full_indexed:
		p = Image.fromarray(idx, mode="P")
		p.putpalette(full_palette)
		frames.append(p)

	return frames, {"transparency": trans_idx, "disposal": 2}


def _save_output_for_ui(frames, durations, loop, gif_save_opts, filename_prefix):
	temp_dir = folder_paths.get_temp_directory()
	os.makedirs(temp_dir, exist_ok=True)

	full_output_folder, filename, _, subfolder, _ = folder_paths.get_save_image_path(filename_prefix, temp_dir)
	os.makedirs(full_output_folder, exist_ok=True)

	max_counter = 0
	matcher = re.compile(f"{re.escape(filename)}_(\\d+)\\D*\\..+", re.IGNORECASE)
	for existing_file in os.listdir(full_output_folder):
		match = matcher.fullmatch(existing_file)
		if match:
			max_counter = max(max_counter, int(match.group(1)))

	file = f"{filename}_{max_counter + 1:05}.gif"
	file_path = os.path.join(full_output_folder, file)

	save_kwargs = {
		"save_all": True,
		"append_images": frames[1:],
		"duration": [max(1, int(v)) for v in durations],
		"loop": int(loop),
		"optimize": True,
	}
	save_kwargs.update(gif_save_opts)

	frames[0].save(
		file_path,
		**save_kwargs,
	)

	return {
		"filename": file,
		"subfolder": subfolder,
		"type": "temp",
		"format": "image/gif",
		"fullpath": file_path,
	}


def _run_gifsicle_optimize(gif_path, use_alpha=False):
	gifsicle_path = shutil.which("gifsicle")
	if not gifsicle_path:
		return

	tmp_out = gif_path + ".opt.gif"
	cmd = [gifsicle_path, "-O3"]
	if use_alpha:
		cmd += ["--disposal=background"]
	cmd += [gif_path, "-o", tmp_out]
	try:
		subprocess.run(cmd, capture_output=True, check=True)
		if os.path.exists(tmp_out) and os.path.getsize(tmp_out) > 0:
			os.replace(tmp_out, gif_path)
	except Exception:
		if os.path.exists(tmp_out):
			try:
				os.remove(tmp_out)
			except Exception:
				pass
