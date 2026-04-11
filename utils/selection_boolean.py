def _input_index(key: str) -> int:
	if not key.startswith("input"):
		return -1
	suffix = key[5:]
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


class AnyType(str):
	def __eq__(self, __value: object) -> bool:
		return True

	def __ne__(self, __value: object) -> bool:
		return False


ANY_TYPE = AnyType("*")


class _DynamicToggleOptions(dict):
	def __init__(self, prefix: str = "select"):
		super().__init__()
		self.prefix = prefix
		self.template = (
			"BOOLEAN",
			{
				"default": False,
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


class SelectionBoolean:
	@classmethod
	def INPUT_TYPES(cls):
		return {
			"required": {},
			"optional": _DynamicToggleOptions(),
		}

	RETURN_TYPES = (ANY_TYPE,)
	RETURN_NAMES = ("output",)
	FUNCTION = "func"
	CATEGORY = "🐴GHTools/Utils"

	def _connected_inputs(self, kwargs):
		connected = []
		for key, value in kwargs.items():
			if not key.startswith("input"):
				continue
			idx = _input_index(key)
			if idx < 0 or value is None:
				continue
			connected.append((idx, value, bool(kwargs.get(f"select_{idx}", False))))
		connected.sort(key=lambda item: item[0])
		return connected

	def func(self, **kwargs):
		connected = self._connected_inputs(kwargs)
		if not connected:
			return (None,)

		enabled = [value for _, value, is_enabled in connected if is_enabled]
		if enabled:
			return (enabled[0],)

		return (connected[0][1],)
