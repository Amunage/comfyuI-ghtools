import os
import re
import subprocess

from .image_autoloader import IMAGE_EXTENSIONS


DEFAULT_LLAMA_CLI_PATH = r"D:\llama.cpp\llama-cli.exe"
DEFAULT_MODEL_PATH = r"D:\llama.cpp\models\supergemma4\supergemma4-26b-abliterated-multimodal-Q4_K_M.gguf"
DEFAULT_MMPROJ_PATH = r"D:\llama.cpp\models\supergemma4\mmproj-supergemma4-26b-abliterated-multimodal-f16.gguf"

TEMPERATURE = 0.7
TOP_P = 0.9
TOP_K = 40
REPEAT_PENALTY = 1.1
MAX_TOKENS = 2048
CTX_SIZE = 4096
THREADS = 8
TIMEOUT_SECONDS = 180
BANNER_CHARS = {"▄", "█", "▀", " "}

INSTRUCTION_PROMPT = (
    "Analyze the image in detailed natural English. "
    "Describe only what is directly visible. "
    "Do not imagine future actions, intent, or hidden context. "
    "Focus on the subject's current action, pose, body posture, hand and arm position, leg position, gaze direction, facial expression, and any visible interaction with objects or the environment. "
    "Be thorough and specific, but give the highest priority to describing what the subject is doing right now. "
    "Describe the current action and body position first, then cover facial expression and gaze, clothing and accessories, visible objects or props, background and environment, lighting and color mood, and overall composition. "
    "Return plain English text only. "
    "Do not use XML, JSON, markdown, roleplay, or extra labels. "
    "Write 5 to 8 detailed sentences."
)


def _debug(message: str):
    print(f"[GHLLMPromptI2T] {message}")


def _validate_file(path: str, label: str, extensions=None) -> str:
    path = os.path.normpath((path or "").strip().strip('"'))
    if not path:
        raise RuntimeError(f"{label} path is empty.")
    if not os.path.isfile(path):
        raise RuntimeError(f"{label} file was not found: {path}")
    if extensions:
        ext = os.path.splitext(path)[1].lower()
        if ext not in extensions:
            raise RuntimeError(f"{label} has an unsupported file type: {path}")
    return path


def _sanitize_text(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x00", "").replace("\x1a", "")
    text = re.sub(r"<[^>\n]*>", "", text)
    text = re.sub(r"llama_memory_breakdown_print:.*$", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or 32 <= ord(ch) <= 126)
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_leading_response_label(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""

    lines = text.split("\n")
    first = lines[0].strip()
    match = re.match(r"^([A-Za-z][A-Za-z0-9 _-]{0,24}):\s+(.+)$", first)
    if match:
        label = match.group(1).strip().lower()
        if label not in {"http", "https", "file", "path"}:
            lines[0] = match.group(2).strip()

    return "\n".join(line for line in lines if line.strip()).strip()


def _is_banner_line(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and all(ch in BANNER_CHARS for ch in stripped)


def _clean_response_text(raw: str, prompt_text: str) -> str:
    text = (raw or "").replace("\r\n", "\n")
    text = re.sub(r"llama_memory_breakdown_print:.*$", "", text, flags=re.IGNORECASE | re.DOTALL)
    lines = []
    skip_prefixes = (
        "priority instruction:",
        "base task:",
        "extra instruction:",
        "additional instruction:",
        "loading model",
        "build",
        "model",
        "modalities",
        "available commands",
        "chat history cleared",
        "loaded media from",
        "exiting...",
        "ggml_cuda_init",
        "load_backend",
        "llama_memory_breakdown_print",
        "device ",
        "nvidia ",
        "/exit or ctrl+c",
        "/regen",
        "/clear",
        "/read ",
        "/glob ",
        "/image ",
    )

    for line in text.split("\n"):
        stripped = line.strip()
        lower = stripped.lower()
        if not stripped:
            continue
        if stripped == prompt_text.strip():
            continue
        if stripped.startswith(">"):
            continue
        if stripped.startswith("[ Prompt:"):
            continue
        if lower.startswith(skip_prefixes):
            continue
        if "compute capability" in lower and "vram:" in lower:
            continue
        if _is_banner_line(stripped):
            continue
        lines.append(stripped)

    return _strip_leading_response_label(_sanitize_text("\n".join(lines)))


def _extract_analysis(text: str) -> str:
    match = re.search(r"Analysis:\s*(.+)$", text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return _sanitize_text(match.group(1))
    return _sanitize_text(text)


def _build_prompt(extra_instruction: str) -> str:
    extra_instruction = _sanitize_text(extra_instruction)
    if not extra_instruction:
        return INSTRUCTION_PROMPT
    return (
        f"{INSTRUCTION_PROMPT}\n"
        "Reference instruction: Use the following as additional guidance while following the base task above. "
        "Treat it as supplementary context, not a replacement for the base task.\n"
        f"Extra instruction: {extra_instruction}"
    )


def _run_single_turn(llama_cli_path: str, model_path: str, mmproj_path: str, image_path: str, prompt_text: str) -> str:
    command = [
        llama_cli_path,
        "-m",
        model_path,
        "--mmproj",
        mmproj_path,
        "--simple-io",
        "--single-turn",
        "--no-warmup",
        "--reasoning",
        "off",
        "--log-colors",
        "off",
        "--color",
        "off",
        "--temp",
        str(TEMPERATURE),
        "--top-p",
        str(TOP_P),
        "--top-k",
        str(TOP_K),
        "--repeat-penalty",
        str(REPEAT_PENALTY),
        "-n",
        str(MAX_TOKENS),
        "-c",
        str(CTX_SIZE),
        "-t",
        str(THREADS),
        "--image",
        image_path,
        "-p",
        prompt_text,
    ]
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore",
        cwd=os.path.dirname(llama_cli_path),
        timeout=TIMEOUT_SECONDS,
    )
    return result.stdout or ""


class LLMPromptI2T:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "llama_cli_path": (
                    "STRING",
                    {
                        "default": DEFAULT_LLAMA_CLI_PATH,
                        "multiline": False,
                        "placeholder": "path to llama-cli.exe",
                    },
                ),
                "model_path": (
                    "STRING",
                    {
                        "default": DEFAULT_MODEL_PATH,
                        "multiline": False,
                        "placeholder": "path to multimodal gguf model",
                    },
                ),
                "mmproj_path": (
                    "STRING",
                    {
                        "default": DEFAULT_MMPROJ_PATH,
                        "multiline": False,
                        "placeholder": "path to mmproj gguf",
                    },
                ),
                "image_path": (
                    "STRING",
                    {
                        "forceInput": True,
                    },
                ),
                "extra_instruction": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "placeholder": "optional extra instruction appended to the default prompt",
                    },
                ),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("analysis",)
    FUNCTION = "generate"
    CATEGORY = "🐴GHTools/Utils"

    @classmethod
    def IS_CHANGED(cls, image_path=""):
        path = os.path.normpath((image_path or "").strip().strip('"'))
        if path and os.path.isfile(path):
            return f"{path}_{os.path.getmtime(path)}"
        return image_path

    def generate(self, llama_cli_path: str, model_path: str, mmproj_path: str, image_path: str, extra_instruction: str):
        llama_cli_path = _validate_file(llama_cli_path, "llama-cli")
        model_path = _validate_file(model_path, "model")
        mmproj_path = _validate_file(mmproj_path, "mmproj")
        image_path = _validate_file(image_path, "image", IMAGE_EXTENSIONS)
        prompt_text = _build_prompt(extra_instruction)

        _debug(f"llama_cli_path={llama_cli_path}")
        _debug(f"model_path={model_path}")
        _debug(f"mmproj_path={mmproj_path}")
        _debug(f"image_path={image_path}")
        _debug("running single-turn multimodal prompt")

        raw_output = _run_single_turn(llama_cli_path, model_path, mmproj_path, image_path, prompt_text)
        cleaned_output = _clean_response_text(raw_output, prompt_text)
        _debug(f"raw_output={cleaned_output}")

        analysis = _extract_analysis(cleaned_output)
        if not analysis:
            raise RuntimeError(
                "single-turn output did not contain an analysis body.\n"
                f"raw:\n{cleaned_output}"
            )

        _debug(f"analysis={analysis}")
        return (analysis,)
