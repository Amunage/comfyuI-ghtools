import os
import re
import subprocess
import tempfile


DEFAULT_LLAMA_CLI_PATH = r"D:\llama.cpp\llama-cli.exe"
DEFAULT_MODEL_PATH = r"D:\llama.cpp\models\supergemma4\supergemma4-26b-abliterated-multimodal-Q4_K_M.gguf"

TEMPERATURE = 0.7
MAX_TOKENS = 2048
CTX_SIZE = 4096
THREADS = 8
TIMEOUT_SECONDS = 60
BANNER_CHARS = {"▄", "█", "▀", " "}

INSTRUCTION_PROMPT = (
    "Translate this into natural English. "
)


def _debug(message: str):
    print(f"[GHLLMPromptT2T] {message}")


def _validate_file(path: str, label: str) -> str:
    path = os.path.normpath((path or "").strip().strip('"'))
    if not path:
        raise RuntimeError(f"{label} path is empty.")
    if not os.path.isfile(path):
        raise RuntimeError(f"{label} file was not found: {path}")
    return path


def _build_prompt(text: str, extra_instruction: str) -> str:
    text = (text or "").strip()
    extra_instruction = (extra_instruction or "").strip()

    if not text:
        raise RuntimeError("input text is empty.")

    prompt_text = (
        INSTRUCTION_PROMPT
        + f"Output only the translation, with no explanation: {text}"
    )
    if extra_instruction:
        prompt_text += f"\nAdditional instruction: {extra_instruction}"

    return prompt_text


def _is_banner_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return all(char in BANNER_CHARS for char in stripped)


def _is_metadata_line(line: str, prompt_text: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True

    lower = stripped.lower()

    if _is_banner_line(stripped):
        return True

    if stripped == prompt_text.strip():
        return True

    metadata_prefixes = (
        "loading model",
        "build",
        "model",
        "modalities",
        "available commands",
        "using custom system prompt",
        "translate this into natural english. output only the translation, with no explanation:",
        "additional instruction:",
        "english translation:",
        "exiting...",
        "ggml_cuda_init",
        "load_backend",
        "llama_memory_breakdown_print",
        "device ",
        "nvidia ",
    )

    if lower.startswith(metadata_prefixes):
        return True

    if lower.startswith("/"):
        return True

    if stripped.startswith(">"):
        return True

    if lower.startswith("prompt:") or lower.startswith("generation:"):
        return True

    if "compute capability" in lower and "vram:" in lower:
        return True

    return False


def _strip_end_thinking(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""

    parts = re.split(r"\[End thinking\]", text, flags=re.IGNORECASE)
    if len(parts) > 1:
        return parts[-1].strip()

    return text


def _extract_result_text(output: str, prompt_text: str) -> str:
    if not output or not output.strip():
        return ""

    text = output.replace("\r\n", "\n")
    text = text.replace("\x00", "").replace("\x1a", "")

    marker = f"> {prompt_text.strip()}"
    if marker in text:
        text = text.split(marker, 1)[1]
    elif prompt_text.strip() in text:
        text = text.split(prompt_text.strip(), 1)[1]

    if "English translation:" in text:
        text = text.split("English translation:", 1)[1]

    for stop_marker in ("\n[ Prompt:", "\n> \n", "\nExiting...", "\nllama_memory_breakdown_print:"):
        if stop_marker in text:
            text = text.split(stop_marker, 1)[0]

    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if _is_metadata_line(stripped, prompt_text):
            continue
        lines.append(stripped)

    return _strip_end_thinking("\n".join(lines).strip())


def _run_single_turn(llama_cli_path: str, model_path: str, prompt_text: str) -> str:
    command = [
        llama_cli_path,
        "-m",
        model_path,
        "-f",
        "",
        "-n",
        str(MAX_TOKENS),
        "--temp",
        str(TEMPERATURE),
        "--no-display-prompt",
        "--no-warmup",
        "--log-colors",
        "off",
        "--color",
        "off",
    ]

    if CTX_SIZE > 0:
        command.extend(["-c", str(CTX_SIZE)])

    if THREADS > 0:
        command.extend(["-t", str(THREADS)])

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    temp_prompt_path = None

    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".txt") as temp_file:
            temp_file.write(prompt_text)
            temp_prompt_path = temp_file.name

        command[4] = temp_prompt_path

        completed = subprocess.run(
            command,
            input="/exit\n",
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="ignore",
            cwd=os.path.dirname(llama_cli_path),
            timeout=max(1, TIMEOUT_SECONDS),
            creationflags=creation_flags,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"local LLM execution failed: timed out after {TIMEOUT_SECONDS} seconds.") from exc
    except Exception as exc:
        raise RuntimeError(f"local LLM execution failed: {exc}") from exc
    finally:
        if temp_prompt_path and os.path.isfile(temp_prompt_path):
            try:
                os.remove(temp_prompt_path)
            except OSError:
                pass

    stdout = completed.stdout or ""
    stderr = (completed.stderr or "").strip()

    if completed.returncode != 0:
        error_message = stderr or stdout[-1000:] or "unknown error"
        raise RuntimeError(f"local LLM execution failed: {error_message}")

    return stdout


class LLMPromptT2T:
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
                        "placeholder": "path to .gguf model",
                    },
                ),
                "text": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "placeholder": "text to translate",
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
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result",)
    FUNCTION = "generate"
    CATEGORY = "🐴GHTools/Utils"

    def generate(self, llama_cli_path: str, model_path: str, text: str, extra_instruction: str):
        llama_cli_path = _validate_file(llama_cli_path, "llama-cli")
        model_path = _validate_file(model_path, "model")
        prompt_text = _build_prompt(text, extra_instruction)

        _debug(f"llama_cli_path={llama_cli_path}")
        _debug(f"model_path={model_path}")
        _debug("running single-turn text prompt")

        raw_output = _run_single_turn(llama_cli_path, model_path, prompt_text)
        _debug(f"raw_output={raw_output}")

        result = _extract_result_text(raw_output, prompt_text)
        if not result:
            raise RuntimeError("local LLM response error: result text is empty.")

        _debug(f"result={result}")
        return (result,)
