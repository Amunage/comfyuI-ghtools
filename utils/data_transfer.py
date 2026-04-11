class AnyType(str):
	"""모든 타입과 매칭되는 특수 타입"""

	def __eq__(self, __value: object) -> bool:
		return True

	def __ne__(self, __value: object) -> bool:
		return False


ANY_TYPE = AnyType("*")
PACKET_MARKER = "__ghtools_data_packet__"


class DataTransferSender:
	@classmethod
	def INPUT_TYPES(cls):
		return {
			"required": {
				"input_1": (ANY_TYPE,),
				"input_2": (ANY_TYPE,),
				"input_3": (ANY_TYPE,),
				"input_4": (ANY_TYPE,),
			}
		}

	RETURN_TYPES = (ANY_TYPE,)
	RETURN_NAMES = ("packet",)
	FUNCTION = "pack"
	CATEGORY = "🐴GHTools/Utils"

	def pack(self, input_1, input_2, input_3, input_4):
		packet = {
			PACKET_MARKER: True,
			"values": [input_1, input_2, input_3, input_4],
		}
		return (packet,)


class DataTransferReceiver:
	@classmethod
	def INPUT_TYPES(cls):
		return {
			"required": {
				"packet": (ANY_TYPE,),
			}
		}

	RETURN_TYPES = (ANY_TYPE, ANY_TYPE, ANY_TYPE, ANY_TYPE)
	RETURN_NAMES = ("output_1", "output_2", "output_3", "output_4")
	FUNCTION = "unpack"
	CATEGORY = "🐴GHTools/Utils"

	def unpack(self, packet):
		values = self._extract_values(packet)
		return tuple(values)

	@staticmethod
	def _extract_values(packet):
		if isinstance(packet, dict) and packet.get(PACKET_MARKER) is True:
			values = packet.get("values", [])
		elif isinstance(packet, (list, tuple)):
			values = list(packet)
		else:
			raise ValueError("DataTransferReceiver: sender packet input is invalid.")

		if len(values) != 4:
			raise ValueError("DataTransferReceiver: packet must contain exactly 4 values.")

		return values


NODE_CLASS_MAPPINGS = {
	"GHDataTransferSender": DataTransferSender,
	"GHDataTransferReceiver": DataTransferReceiver,
}

NODE_DISPLAY_NAME_MAPPINGS = {
	"GHDataTransferSender": "🐴Data Sender",
	"GHDataTransferReceiver": "🐴Data Receiver",
}
