from .text_switch import TextSwitch
from .text_concatenate import TextConcatenate
from .text_concatenate import TextConcatenateToggle

from .image_autoloader import ImageAutoloader
from .image_resolution import ImageResolutionNode
from .image_comparer import ImageComparer
from .image_mask import ImageMask
from .image_crop import ImageCrop

from .video_preview import VideoPreview
from .gif_decomposer import GifDecomposer
from .gif_assembler import GifAssembler

from .audio_preview import AudioPreview
from .audio_controller import AudioController

from .generate_llm import GenerateLLM
from .prompt_buffer import PromptBuffer
from .steps_cfg_value import StepsCfgValue
from .convert_value import ConvertValue
from .selection_output import ForkSelection
from .selection_input import AnySelection


NODE_CLASS_MAPPINGS = {
	"GHTextSwitch": TextSwitch,
	"GHtextConcatenate": TextConcatenate,
	"GHtextConcatenateToggle": TextConcatenateToggle,
    
    "GHImageAutoloader": ImageAutoloader,
	"GHImageComparer": ImageComparer,
	"GHImageResolutionNode": ImageResolutionNode,
	"GHImageMask": ImageMask,
	"GHImageCrop": ImageCrop,
    
	"GHVideoPreview": VideoPreview,
	"GHGifDecomposer": GifDecomposer,
	"GHGifAssembler": GifAssembler,
    
	"GHAudioPreview": AudioPreview,
	"GHAudioController": AudioController,
    
	"GHGenerateLLM": GenerateLLM,
	"GHPromptBuffer": PromptBuffer,
	"GHStepsCfgValue": StepsCfgValue,
	"GHConvertValue": ConvertValue,
	"GHForkSelection": ForkSelection,
	"GHAnySelection": AnySelection,	
}

NODE_DISPLAY_NAME_MAPPINGS = {


	"GHTextSwitch": "🐴 Text Switch",
	"GHtextConcatenate": "🐴 Text Concatenate",
	"GHtextConcatenateToggle": "🐴 Text Concatenate (Toggle)",
    
    "GHImageAutoloader": "🐴 Image Autoloader",
	"GHImageComparer": "🐴 Image Comparer",
	"GHImageResolutionNode": "🐴 Image Resolution",
	"GHImageMask": "🐴 Image Mask",
	"GHImageCrop": "🐴 Image Crop",
    
	"GHVideoPreview": "🐴 Video Preview",
	"GHGifDecomposer": "🐴 GIF Decomposer",
	"GHGifAssembler": "🐴 GIF Assembler",
    
	"GHAudioPreview": "🐴 Audio Preview",
	"GHAudioController": "🐴 Audio Controller",
    
	"GHGenerateLLM": "🐴 Generate LLM",
	"GHPromptBuffer": "🐴 Prompt Buffer",
	"GHStepsCfgValue": "🐴 Steps CFG Value",
	"GHConvertValue": "🐴 Convert Value",
	"GHForkSelection": "🐴 Selection Output",
	"GHAnySelection": "🐴 Selection Input",
	
}

__all__ = [
	"NODE_CLASS_MAPPINGS",
	"NODE_DISPLAY_NAME_MAPPINGS",
]
