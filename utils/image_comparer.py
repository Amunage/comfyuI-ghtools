from nodes import PreviewImage


class ImageComparer(PreviewImage):
  """A node that compares two images in the UI."""

  NAME = 'GH Image Comparer'
  CATEGORY = 'GHTools/Utils'
  FUNCTION = "compare_images"
  DESCRIPTION = "Compares two images with a hover slider, or click from properties."
  
  RETURN_TYPES = ("IMAGE", "IMAGE")
  RETURN_NAMES = ("image_a", "image_b")
  OUTPUT_NODE = True

  @classmethod
  def INPUT_TYPES(cls):  # pylint: disable = invalid-name, missing-function-docstring
    return {
      "required": {},
      "optional": {
        "image_a": ("IMAGE",),
        "image_b": ("IMAGE",),
      },
      "hidden": {
        "prompt": "PROMPT",
        "extra_pnginfo": "EXTRA_PNGINFO"
      },
    }

  def compare_images(self,
                     image_a=None,
                     image_b=None,
                     filename_prefix="gh.compare.",
                     prompt=None,
                     extra_pnginfo=None):

    result = { "ui": { "a_images":[], "b_images": [] } }
    if image_a is not None and len(image_a) > 0:
      result['ui']['a_images'] = self.save_images(image_a, filename_prefix, prompt, extra_pnginfo)['ui']['images']

    if image_b is not None and len(image_b) > 0:
      result['ui']['b_images'] = self.save_images(image_b, filename_prefix, prompt, extra_pnginfo)['ui']['images']

    result["result"] = (image_a, image_b)
    return result