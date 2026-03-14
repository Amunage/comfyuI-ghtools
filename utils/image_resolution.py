class ImageResolutionNode:
	"""직접 입력 혹은 프리셋으로 이미지 해상도를 선택하는 노드."""

	# (ratio, width, height)
	_PRESET_ROWS = [
		("3:4", 416, 544),
		("3:4", 560, 720),
		("3:4", 672, 864),
		("3:4", 720, 912),
		("3:4", 784, 1008),
		("3:4", 848, 1088),
		("3:4", 896, 1152),
		("2:3", 384, 576),
		("2:3", 528, 768),
		("2:3", 624, 912),
		("2:3", 656, 960),
		("2:3", 736, 1072),
		("2:3", 784, 1136),
		("2:3", 832, 1216),
		("4:3", 1152, 896),
		("9:16", 368, 624),
		("9:16", 480, 848),
		("9:16", 576, 1008),
		("9:16", 608, 1072),
		("9:16", 672, 1184),
		("9:16", 720, 1264),
		("9:16", 768, 1344),
		("9:21", 640, 1536),
	]

	_PRESET_MAP = {
		"custom": (0, 0),  # placeholder, 실제 사용 시 무시됨
	}
	for ratio, w, h in _PRESET_ROWS:
		text = f"{ratio} | {w}x{h}"
		_PRESET_MAP[text] = (w, h)

	@classmethod
	def _preset_options(cls):
		return list(cls._PRESET_MAP.keys())

	@classmethod
	def INPUT_TYPES(cls):
		return {
			"required": {
				"preset": (
					cls._preset_options(),
					{"default": "custom"},
				),
				"width": (
					"INT",
					{"default": 480, "min": 64, "max": 8192, "step": 8},
				),
				"height": (
					"INT",
					{"default": 720, "min": 64, "max": 8192, "step": 8},
				),
			}
		}

	RETURN_TYPES = ("INT", "INT")
	RETURN_NAMES = ("width", "height")
	FUNCTION = "resolve"
	CATEGORY = "🐴GHTools/Utils"

	def resolve(self, preset, width, height):
		if preset != "custom":
			width, height = self._PRESET_MAP[preset]
		return (int(width), int(height))
