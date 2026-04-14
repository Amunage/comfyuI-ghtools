import os
import subprocess
import tempfile


DEFAULT_SYSTEM_PROMPT = ""

ASCII_BANNER_CHARS = set("▄█▀ ")


def _comfyui_root_dir():
	return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def _build_request_text(user_text: str):
	clean_text = (user_text or "").strip()
	return f"Translate this into natural English. Output only the translation, with no explanation: {clean_text}"


def _is_banner_line(line: str):
	stripped = line.strip()
	if not stripped:
		return False
	return all(char in ASCII_BANNER_CHARS for char in stripped)


def _is_metadata_line(line: str, prompt_text: str):
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
		"english translation:",
		"exiting...",
	)

	if lower.startswith(metadata_prefixes):
		return True

	if lower.startswith("/"):
		return True

	if stripped.startswith(">"):
		return True

	if lower.startswith("prompt:") or lower.startswith("generation:"):
		return True

	return False


def _extract_generated_text(output: str, prompt_text: str):
	if not output or not output.strip():
		return ""

	text = output.replace("\r\n", "\n")
	marker = f"> {prompt_text.strip()}"

	if marker in text:
		text = text.split(marker, 1)[1]
	elif prompt_text.strip() in text:
		text = text.split(prompt_text.strip(), 1)[1]

	if "English translation:" in text:
		text = text.split("English translation:", 1)[1]

	for stop_marker in ("\n[ Prompt:", "\n> \n", "\nExiting..."):
		if stop_marker in text:
			text = text.split(stop_marker, 1)[0]

	lines = []
	for line in text.split("\n"):
		stripped = line.strip()
		if _is_metadata_line(stripped, prompt_text):
			continue
		lines.append(stripped)

	return "\n".join(lines).strip()


class GenerateLocalLLM:
	"""
	llama.cpp의 로컬 GGUF 모델을 한 번 실행해 ComfyUI 프롬프트를 생성하는 노드.
	실행 후 즉시 종료되며, llama-cli에 /exit를 stdin으로 전달해 상주하지 않는다.
	"""

	@classmethod
	def INPUT_TYPES(cls):
		return {
			"required": {
				"switch": (
					"BOOLEAN",
					{
						"default": True,
						"label_on": "ON",
						"label_off": "OFF",
					},
				),
				"llama_cli_path": (
					"STRING",
					{
						"default": "",
						"multiline": False,
						"placeholder": "path to llama-cli.exe",
					},
				),
				"model_path": (
					"STRING",
					{
						"default": "",
						"multiline": False,
						"placeholder": "path to .gguf model",
					},
				),
				"system_prompt": (
					"STRING",
					{
						"default": DEFAULT_SYSTEM_PROMPT,
						"multiline": True,
						"placeholder": "optional system prompt",
					},
				),
				"text": (
					"STRING",
					{
						"default": "",
						"multiline": True,
						"placeholder": "문장을 입력하세요",
					},
				),
				"temperature": (
					"FLOAT",
					{
						"default": 0.2,
						"min": 0.0,
						"max": 2.0,
						"step": 0.05,
					},
				),
				"max_tokens": (
					"INT",
					{
						"default": 1024,
						"min": 1,
						"max": 4096,
						"step": 1,
					},
				),
				"ctx_size": (
					"INT",
					{
						"default": 2048,
						"min": 0,
						"max": 8192,
						"step": 1,
					},
				),
				"threads": (
					"INT",
					{
						"default": 8,
						"min": 0,
						"max": 128,
						"step": 1,
					},
				),
				"timeout_seconds": (
					"INT",
					{
						"default": 60,
						"min": 10,
						"max": 3600,
						"step": 1,
					},
				),
			},
		}

	RETURN_TYPES = ("STRING",)
	RETURN_NAMES = ("result",)
	FUNCTION = "generate"
	CATEGORY = "🐴GHTools/Utils"

	def generate(
		self,
		switch: bool,
		llama_cli_path: str,
		model_path: str,
		system_prompt: str,
		text: str,
		temperature: float,
		max_tokens: int,
		ctx_size: int,
		threads: int,
		timeout_seconds: int,
	):
		if not switch:
			return (text,)

		if not text or not text.strip():
			raise RuntimeError("로컬 LLM 실행 실패: 입력 문장이 비어 있습니다.")

		llama_cli_path = (llama_cli_path or "").strip()
		model_path = (model_path or "").strip()
		system_prompt = (system_prompt or "").strip()
		prompt_text = text.strip()
		request_text = _build_request_text(prompt_text)

		if not llama_cli_path:
			raise RuntimeError("로컬 LLM 실행 실패: llama_cli_path 값이 비어 있습니다.")
		if not model_path:
			raise RuntimeError("로컬 LLM 실행 실패: model_path 값이 비어 있습니다.")
		if not os.path.isfile(llama_cli_path):
			raise RuntimeError(f"로컬 LLM 실행 실패: llama-cli를 찾을 수 없습니다. {llama_cli_path}")
		if not os.path.isfile(model_path):
			raise RuntimeError(f"로컬 LLM 실행 실패: GGUF 모델을 찾을 수 없습니다. {model_path}")

		command = [
			llama_cli_path,
			"-m",
			model_path,
			"-f",
			"",
			"-n",
			str(max_tokens),
			"--temp",
			str(temperature),
			"--no-display-prompt",
			"--no-warmup",
			"--log-colors",
			"off",
			"--color",
			"off",
		]

		if system_prompt:
			command.extend(["-sys", system_prompt])

		if ctx_size > 0:
			command.extend(["-c", str(ctx_size)])

		if threads > 0:
			command.extend(["-t", str(threads)])

		creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
		temp_prompt_path = None

		try:
			with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".txt") as temp_file:
				temp_file.write(request_text)
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
				timeout=max(1, timeout_seconds),
				creationflags=creation_flags,
			)
		except subprocess.TimeoutExpired as exc:
			raise RuntimeError(
				f"로컬 LLM 실행 실패: 제한 시간 {timeout_seconds}초를 초과했습니다."
			) from exc
		except Exception as exc:
			raise RuntimeError(f"로컬 LLM 실행 실패: {exc}") from exc
		finally:
			if temp_prompt_path and os.path.isfile(temp_prompt_path):
				try:
					os.remove(temp_prompt_path)
				except OSError:
					pass

		stdout = completed.stdout or ""
		stderr = (completed.stderr or "").strip()

		if completed.returncode != 0:
			error_message = stderr or stdout[-1000:] or "알 수 없는 오류"
			raise RuntimeError(f"로컬 LLM 실행 실패: {error_message}")

		result_text = _extract_generated_text(stdout, request_text)

		if not result_text:
			raise RuntimeError("로컬 LLM 응답 오류: 결과 텍스트가 비어 있습니다.")

		return (result_text,)