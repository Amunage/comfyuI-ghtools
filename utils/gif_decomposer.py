import hashlib
import json
import os
import re

import numpy as np
import torch
from PIL import Image, ImageSequence

import folder_paths


DEFAULT_PREVIEW_MAX_FRAMES = 0


def _descriptor(frame_uint8: np.ndarray, size: int = 16) -> np.ndarray:
	gray = Image.fromarray(frame_uint8).convert("L").resize((size, size), Image.Resampling.BILINEAR)
	return np.asarray(gray, dtype=np.float32) / 255.0


def _resolve_gif_path(gif_path: str) -> str:
	if not gif_path or not str(gif_path).strip():
		raise ValueError("gif_path is empty")

	raw = str(gif_path).strip().strip('"')

	if os.path.isabs(raw) and os.path.exists(raw):
		return raw

	input_dir = folder_paths.get_input_directory()
	candidate = os.path.join(input_dir, raw)
	if os.path.exists(candidate):
		return candidate

	if os.path.exists(raw):
		return raw

	raise ValueError(f"GIF file not found: {gif_path}")


def _load_gif_frames(path: str, default_duration_ms: int):
	frames = []
	durations = []

	with Image.open(path) as img:
		loop = int(img.info.get("loop", 0))
		for frame in ImageSequence.Iterator(img):
			rgba = frame.convert("RGBA")
			frame_np = np.asarray(rgba, dtype=np.uint8)
			frames.append(frame_np)
			durations.append(int(frame.info.get("duration", default_duration_ms)))

	if not frames:
		raise ValueError("No frames found in GIF")

	return np.stack(frames, axis=0), durations, loop


def _build_temp_preview_gif(frames: np.ndarray, durations_ms, filename_prefix: str):
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

	pil_frames = [Image.fromarray(frame[:, :, :3]) for frame in frames]
	first_p = pil_frames[0].quantize(colors=256, method=Image.Quantize.MEDIANCUT)
	quantized = [first_p]
	for frame in pil_frames[1:]:
		quantized.append(frame.quantize(palette=first_p))

	quantized[0].save(
		file_path,
		save_all=True,
		append_images=quantized[1:],
		duration=[max(1, int(v)) for v in durations_ms],
		loop=0,
		optimize=True,
		disposal=2,
	)

	return {
		"filename": file,
		"subfolder": subfolder,
		"type": "temp",
		"format": "image/gif",
		"fullpath": file_path,
	}


class GifDecomposer:
	"""
	GIF 파일을 로드해 중복 프레임을 제거하고 타임라인 JSON을 출력.
	"""

	@classmethod
	def INPUT_TYPES(cls):
		return {
			"required": {
				"gif_path": ("STRING", {"default": "", "placeholder": "input/icon_1.gif or absolute path"}),
				"dedupe_mode": (("original", "exact", "near", "jump"), {"default": "exact"}),
				"near_threshold": (
					"FLOAT",
					{"default": 0.005, "min": 0.0, "max": 0.25, "step": 0.001},
				),
				"jump_step": (
					"INT",
					{"default": 2, "min": 2, "max": 100, "step": 1},
				),
				"default_duration_ms": (
					"INT",
					{"default": 100, "min": 1, "max": 60000, "step": 1},
				),
			},
			"hidden": {
				"prompt": "PROMPT",
				"extra_pnginfo": "EXTRA_PNGINFO",
			}
		}

	RETURN_TYPES = ("IMAGE", "STRING")
	RETURN_NAMES = ("image", "image_info")
	FUNCTION = "decompose"
	CATEGORY = "GHTools/Utils"

	@classmethod
	def VALIDATE_INPUTS(cls, gif_path, **kwargs):
		# Allow uploaded/newly-added files even if dropdown cache is stale.
		if gif_path is None:
			return "gif_path is required"
		return True

	def decompose(
		self,
		gif_path,
		dedupe_mode,
		near_threshold,
		jump_step,
		default_duration_ms,
		prompt=None,
		extra_pnginfo=None,
	):
		resolved_path = _resolve_gif_path(gif_path)
		frames, durations_ms, loop = _load_gif_frames(resolved_path, int(default_duration_ms))
		frame_count = int(frames.shape[0])

		unique_frames = []
		frame_to_unique = []

		if dedupe_mode == "jump":
			step = max(2, int(jump_step))
			selected_indices = list(range(0, frame_count, step))
			frames = frames[selected_indices]
			durations_ms = [durations_ms[i] for i in selected_indices]
			frame_count = len(selected_indices)

		if dedupe_mode == "original" or dedupe_mode == "jump":
			for i in range(frame_count):
				unique_frames.append(frames[i])
				frame_to_unique.append(i)
		elif dedupe_mode == "exact":
			key_to_index = {}
			for i in range(frame_count):
				key = hashlib.sha256(frames[i].tobytes()).hexdigest()
				if key in key_to_index:
					frame_to_unique.append(key_to_index[key])
				else:
					uidx = len(unique_frames)
					key_to_index[key] = uidx
					unique_frames.append(frames[i])
					frame_to_unique.append(uidx)
		else:  # near
			unique_descriptors = []
			for i in range(frame_count):
				frame_desc = _descriptor(frames[i])
				matched_index = -1

				for uidx, saved_desc in enumerate(unique_descriptors):
					distance = float(np.mean(np.abs(frame_desc - saved_desc)))
					if distance <= near_threshold:
						matched_index = uidx
						break

				if matched_index >= 0:
					frame_to_unique.append(matched_index)
				else:
					uidx = len(unique_frames)
					unique_frames.append(frames[i])
					unique_descriptors.append(frame_desc)
					frame_to_unique.append(uidx)

		unique_np = np.stack(unique_frames, axis=0)
		unique_tensor = torch.from_numpy(unique_np.astype(np.float32) / 255.0)

		if int(DEFAULT_PREVIEW_MAX_FRAMES) <= 0:
			preview_count = frame_count
		else:
			preview_count = min(int(DEFAULT_PREVIEW_MAX_FRAMES), frame_count)
		preview_info = _build_temp_preview_gif(
			frames=frames[:preview_count],
			durations_ms=durations_ms[:preview_count],
			filename_prefix="gh.gif.loaded.preview",
		)

		timeline = {
			"version": 1,
			"source_gif_path": resolved_path,
			"durations_ms": [max(1, int(v)) for v in durations_ms],
			"frame_to_unique": [int(v) for v in frame_to_unique],
			"original_count": frame_count,
			"unique_count": int(len(unique_frames)),
			"height": int(frames.shape[1]),
			"width": int(frames.shape[2]),
			"loop": loop,
		}

		timeline_json = json.dumps(timeline, ensure_ascii=True)
		return {
			"ui": {
				"gifs": [preview_info],
			},
			"result": (unique_tensor, timeline_json),
		}
