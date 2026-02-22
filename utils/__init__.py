from .steps_cfg_value import StepsCfgValue
from .convert_value import ConvertValue
from .text_concatenate import TextConcatenate
from .text_concatenate import TextConcatenateToggle
from .text_switch import TextSwitch
from .image_resolution import ImageResolutionNode
from .image_comparer import ImageComparer
from .selection_output import ForkSelection
from .selection_input import AnySelection
from .audio_preview import AudioPreview
from .audio_controller import AudioController
from .video_preview import VideoPreview


NODE_CLASS_MAPPINGS = {
	"GHStepsCfgValue": StepsCfgValue,
	"GHConvertValue": ConvertValue,
	"GHtextConcatenate": TextConcatenate,
	"GHtextConcatenateToggle": TextConcatenateToggle,
	"GHTextSwitch": TextSwitch,
	"GHImageResolutionNode": ImageResolutionNode,
	"GHImageComparer": ImageComparer,
	"GHForkSelection": ForkSelection,
	"GHAnySelection": AnySelection,
	"GHAudioPreview": AudioPreview,
	"GHAudioController": AudioController,
	"GHVideoPreview": VideoPreview,
}

NODE_DISPLAY_NAME_MAPPINGS = {
	"GHStepsCfgValue": "GH Steps CFG Value",
	"GHConvertValue": "GH Convert Value",
	"GHtextConcatenate": "GH Text Concatenate",
	"GHtextConcatenateToggle": "GH Text Concatenate (Toggle)",
	"GHTextSwitch": "GH Text Switch",
	"GHImageComparer": "GH Image Comparer",
	"GHImageResolutionNode": "GH Image Resolution",
	"GHForkSelection": "GH Selection Output",
	"GHAnySelection": "GH Selection Input",
	"GHAudioPreview": "GH Audio Preview",
	"GHAudioController": "GH Audio Controller",
	"GHVideoPreview": "GH Video Preview",
}

__all__ = [
	"NODE_CLASS_MAPPINGS",
	"NODE_DISPLAY_NAME_MAPPINGS",
]
