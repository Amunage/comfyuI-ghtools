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
from .generate_llm import GenerateLLM
from .gif_decomposer import GifDecomposer
from .gif_assembler import GifAssembler
from .image_mask import ImageMask
from .image_crop import ImageCrop
from .Prompt_buffer import PromptBuffer
from .image_autoloader import ImageAutoloader


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
	"GHGenerateLLM": GenerateLLM,
	"GHGifDecomposer": GifDecomposer,
	"GHGifAssembler": GifAssembler,
	"GHImageMask": ImageMask,
	"GHImageCrop": ImageCrop,
	"GHPromptBuffer": PromptBuffer,
	"GHImageAutoloader": ImageAutoloader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
	"GHStepsCfgValue": "🐴 Steps CFG Value",
	"GHConvertValue": "🐴 Convert Value",
	"GHtextConcatenate": "🐴 Text Concatenate",
	"GHtextConcatenateToggle": "🐴 Text Concatenate (Toggle)",
	"GHTextSwitch": "🐴 Text Switch",
	"GHImageComparer": "🐴 Image Comparer",
	"GHImageResolutionNode": "🐴 Image Resolution",
	"GHForkSelection": "🐴 Selection Output",
	"GHAnySelection": "🐴 Selection Input",
	"GHAudioPreview": "🐴 Audio Preview",
	"GHAudioController": "🐴 Audio Controller",
	"GHVideoPreview": "🐴 Video Preview",
	"GHGenerateLLM": "🐴 Generate LLM",
	"GHGifDecomposer": "🐴 GIF Decomposer",
	"GHGifAssembler": "🐴 GIF Assembler",
	"GHImageMask": "🐴 Image Mask",
	"GHImageCrop": "🐴 Image Crop",
	"GHPromptBuffer": "🐴 Prompt Buffer",
	"GHImageAutoloader": "🐴 Image Autoloader",
}

__all__ = [
	"NODE_CLASS_MAPPINGS",
	"NODE_DISPLAY_NAME_MAPPINGS",
]
