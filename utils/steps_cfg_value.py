import comfy.samplers


class StepsCfgValue:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "steps": (
                    "INT",
                    {
                        "default": 20,
                        "min": 1,
                        "max": 200,
                        "step": 1,
                        "display": "number",
                        "tooltip": "샘플링 스텝 수",
                    },
                ),
                "cfg": (
                    "FLOAT",
                    {
                        "default": 7.0,
                        "min": 0.0,
                        "max": 30.0,
                        "step": 0.1,
                        "round": 0.1,
                        "display": "number",
                        "tooltip": "CFG 스케일 값",
                    },
                ),
            }
        }

    RETURN_TYPES = ("INT", "FLOAT")
    RETURN_NAMES = ("steps", "cfg")

    FUNCTION = "select"
    CATEGORY = "GHTools/Utils"

    def select(self, steps: int, cfg: float):
        return (max(1, int(steps)), float(cfg))
