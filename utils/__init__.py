from .tag_loader import TagLoader

from .text_switch import TextSwitch
from .text_concatenate import TextConcatenate
from .text_concatenate import TextConcatenateToggle

from .image_autoloader import ImageAutoloader
from .image_resolution import ImageResolutionNode
from .image_comparer import ImageComparer
from .image_mask import ImageMask
from .image_crop import ImageCrop

from .video_combine import VideoCombine
from .gif_decomposer import GifDecomposer
from .gif_assembler import GifAssembler

from .audio_preview import AudioPreview
from .audio_vocalrange import AudioVocalRange

from .generate_llm import GenerateLLM
from .generate_local_llm import GenerateLocalLLM
from .prompt_buffer import PromptBuffer
from .steps_cfg_value import StepsCfgValue
from .convert_value import ConvertValue
from .data_transfer import DataTransferReceiver
from .data_transfer import DataTransferSender
from .selection_boolean import SelectionBoolean
from .selection_output import ForkSelection
from .selection_input import AnySelection


NODE_CLASS_MAPPINGS = {
    "GHTagLoader": TagLoader,
    "GHTextSwitch": TextSwitch,
    "GHtextConcatenate": TextConcatenate,
    "GHtextConcatenateToggle": TextConcatenateToggle,
    "GHImageAutoloader": ImageAutoloader,
    "GHImageComparer": ImageComparer,
    "GHImageResolutionNode": ImageResolutionNode,
    "GHImageMask": ImageMask,
    "GHImageCrop": ImageCrop,
    "GHVideoCombine": VideoCombine,
    "GHGifDecomposer": GifDecomposer,
    "GHGifAssembler": GifAssembler,
    "GHAudioPreview": AudioPreview,
    "GHAudioVocalRange": AudioVocalRange,
    "GHGenerateLLM": GenerateLLM,
    "GHGenerateLocalLLM": GenerateLocalLLM,
    "GHPromptBuffer": PromptBuffer,
    "GHStepsCfgValue": StepsCfgValue,
    "GHConvertValue": ConvertValue,
    "GHDataTransferSender": DataTransferSender,
    "GHDataTransferReceiver": DataTransferReceiver,
    "GHSelectionBoolean": SelectionBoolean,
    "GHForkSelection": ForkSelection,
    "GHAnySelection": AnySelection,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GHTagLoader": "🐴Tag Loader",
    "GHTextSwitch": "🐴Text Switch",
    "GHtextConcatenate": "🐴Text Concatenate",
    "GHtextConcatenateToggle": "🐴Text Concatenate(Toggle)",
    "GHImageAutoloader": "🐴Image Autoloader",
    "GHImageComparer": "🐴Image Comparer",
    "GHImageResolutionNode": "🐴Image Resolution",
    "GHImageMask": "🐴Image Mask",
    "GHImageCrop": "🐴Image Crop",
    "GHVideoCombine": "🐴Video Combine",
    "GHGifDecomposer": "🐴GIF Decomposer",
    "GHGifAssembler": "🐴GIF Assembler",
    "GHAudioPreview": "🐴Audio Preview",
    "GHAudioVocalRange": "🐴Audio Vocal Range",
    "GHGenerateLLM": "🐴Generate LLM",
    "GHGenerateLocalLLM": "🐴Generate Local LLM",
    "GHPromptBuffer": "🐴Prompt Buffer",
    "GHStepsCfgValue": "🐴Steps CFG Value",
    "GHConvertValue": "🐴Convert Value",
    "GHDataTransferSender": "🐴Data Sender",
    "GHDataTransferReceiver": "🐴Data Receiver",
    "GHSelectionBoolean": "🐴Selection Boolean",
    "GHForkSelection": "🐴Selection Output",
    "GHAnySelection": "🐴Selection Input",
}

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
]
