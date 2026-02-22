from .tag_age import TagAgeNode
from .tag_body import TagBodyNode
from .tag_emotion import TagEmotionNode
from .tag_eye import TagEyeNode
from .tag_focus import TagFocusNode
from .tag_genital import TagGenitalNode
from .tag_grade import TagGradeNode
from .tag_hand import TagHandNode
from .tag_humans import TagHumansNode
from .tag_looking import TagLookingNode
from .tag_light import TagLightNode
from .tag_pose import TagPoseNode


NODE_CLASS_MAPPINGS = {
	"TagAgeNode": TagAgeNode,
	"TagBodyNode": TagBodyNode,
	"TagEmotionNode": TagEmotionNode,
	"TagEyeNode": TagEyeNode,
	"TagFocusNode": TagFocusNode,
	"TagGenitalNode": TagGenitalNode,
	"TagGradeNode": TagGradeNode,
	"TagHandNode": TagHandNode,
	"TagHumansNode": TagHumansNode,
	"TagLookingNode": TagLookingNode,
	"TagLightNode": TagLightNode,
	"TagPoseNode": TagPoseNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
	"TagAgeNode": "Tag:Age",
	"TagBodyNode": "Tag:Body",
	"TagEmotionNode": "Tag:Emotion",
	"TagEyeNode": "Tag:Eye",
	"TagFocusNode": "Tag:Focus",
	"TagGenitalNode": "Tag:Genital",
	"TagGradeNode": "Tag:Grade",
	"TagHandNode": "Tag:Hand",
	"TagHumansNode": "Tag:Humans",
	"TagLookingNode": "Tag:Looking",
	"TagLightNode": "Tag:Light",
	"TagPoseNode": "Tag:Pose",
}

__all__ = [
	"NODE_CLASS_MAPPINGS",
	"NODE_DISPLAY_NAME_MAPPINGS",
]
