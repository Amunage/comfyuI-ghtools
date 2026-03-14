import importlib
import subprocess
import sys

try:
	from google import genai
except Exception:
	genai = None


def ensure_google_genai():
	global genai
	if genai is not None:
		return genai

	try:
		subprocess.check_call([sys.executable, "-m", "pip", "install", "google-genai"])
		google_module = importlib.import_module("google")
		genai = getattr(google_module, "genai", None)
		if genai is None:
			genai = importlib.import_module("google.genai")
		return genai
	except Exception as exc:
		raise RuntimeError(
			"LLM 실행 실패: `google-genai` 패키지 자동 설치에 실패했습니다. "
			"직접 `pip install google-genai` 후 다시 시도해 주세요."
		) from exc


class GenerateLLM:
	"""
	입력 문장을 ComfyUI용 자연어 프롬프트로 재작성하는 LLM 노드.
	실행 스위치가 OFF이면 LLM 호출 없이 입력 문장을 그대로 반환.
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
				"model": (
					"STRING",
					{
						"default": "gemini-2.5-flash-lite",
						"multiline": False,
						"placeholder": "gemini model name",
					},
				),
				"api_key": (
					"STRING",
					{
						"default": "",
						"multiline": False,
						"placeholder": "Gemini API Key",
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
			},
		}

	RETURN_TYPES = ("STRING",)
	RETURN_NAMES = ("result",)
	FUNCTION = "generate"
	CATEGORY = "GHTools/Utils"

	def generate(self, switch: bool, model: str, api_key: str, text: str):
		if not switch:
			return (text,)

		if not model or not model.strip():
			raise RuntimeError("LLM 실행 실패: model 값이 비어 있습니다.")

		if not api_key or not api_key.strip():
			raise RuntimeError("LLM 실행 실패: api_key 값이 비어 있습니다.")

		if not text or not text.strip():
			raise RuntimeError("LLM 실행 실패: 입력 문장이 비어 있습니다.")

		system_instruction = (
			"You rewrite user text into a high-quality natural-language prompt for ComfyUI image generation. "
			"Return only the rewritten prompt text. "
			"Do not include explanations, bullet points, JSON, markdown, or code fences. "
			"Preserve the user's core intent, style, and key constraints. "
		)

		payload = {
			"system_instruction": system_instruction,
			"contents": text.strip(),
		}

		genai_module = ensure_google_genai()

		try:
			client = genai_module.Client(api_key=api_key.strip())
			response = client.models.generate_content(
				model=model.strip(),
				contents=payload["contents"],
				config={
					"system_instruction": payload["system_instruction"],
					"temperature": 0.7,
				},
			)
		except Exception as exc:
			raise RuntimeError(f"LLM API 호출 실패: {exc}") from exc

		result_text = (getattr(response, "text", None) or "").strip()

		if not result_text:
			prompt_feedback = getattr(response, "prompt_feedback", None)
			if prompt_feedback:
				raise RuntimeError(f"LLM 생성 거부 또는 실패: {prompt_feedback}")

			candidates = getattr(response, "candidates", None) or []
			if candidates:
				first = candidates[0]
				finish_reason = getattr(first, "finish_reason", None)
				if finish_reason:
					raise RuntimeError(f"LLM 생성 거부 또는 실패: {finish_reason}")

			raise RuntimeError("LLM 응답 오류: 결과 텍스트가 비어 있습니다.")

		if not result_text:
			raise RuntimeError("LLM 응답 오류: 결과 텍스트가 비어 있습니다.")

		return (result_text,)
