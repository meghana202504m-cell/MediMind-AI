import os
from typing import Any

import requests

SUPPORTED_LANGUAGE_CODES = {'en', 'kn', 'hi'}
LANGUAGE_NAMES = {'en': 'English', 'kn': 'Kannada', 'hi': 'Hindi'}


class LLMProvider:
    """Abstraction for local or cloud LLM providers."""

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        raise NotImplementedError

    def generate_structured(self, prompt: str, *, system: str | None = None) -> dict[str, Any]:
        result = self.generate(prompt, system=system)
        try:
            return eval(result, {"__builtins__": {}}, {})
        except Exception:
            return {"text": result}

    def translate(self, text: str, target_language: str) -> str:
        language_code = (target_language or 'en').strip().lower()
        if not text.strip():
            return text
        if language_code == 'en':
            return text
        raise NotImplementedError


class LocalLLMProvider(LLMProvider):
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv('OLLAMA_MODEL', 'gemma3:4b')
        self.base_url = os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434/api/generate')

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        try:
            payload = {
                'model': self.model,
                'prompt': (system or '') + '\n\n' + prompt,
                'stream': False,
            }
            response = requests.post(self.base_url, json=payload, timeout=90)
            response.raise_for_status()
            data = response.json()
            answer = (data.get('response') or '').strip()
            if answer:
                return answer
            return 'The local medical assistant is available but returned an empty response.'
        except requests.RequestException:
            return (
                'Local AI is not available right now. The application remains usable with the built-in medical guidance templates.'
            )

    def translate(self, text: str, target_language: str) -> str:
        if not text.strip():
            return text
        language_code = (target_language or 'en').strip().lower()
        if language_code not in SUPPORTED_LANGUAGE_CODES:
            raise ValueError('Unsupported language code.')
        if language_code == 'en':
            return text
        language_name = LANGUAGE_NAMES[language_code]
        translation_prompt = (
            f'Translate the following medical explanation into {target_language}. '
            'Keep medical values, units, biomarker names, and numerical accuracy unchanged. '
            'Return only the translated text without extra commentary.\n\n{text}'
        )
        return self.generate(translation_prompt)


class CloudLLMProvider(LLMProvider):
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')

    def _available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        if not self._available():
            return 'Cloud AI is not configured. Please set OPENAI_API_KEY or switch the provider to local.'
        return 'Cloud AI provider is configured but not connected in this lightweight build.'

    def translate(self, text: str, target_language: str) -> str:
        if not self._available():
            return text
        return text


def get_llm_provider() -> LLMProvider:
    provider_name = (os.getenv('AI_PROVIDER') or 'local').lower()
    if provider_name == 'cloud':
        return CloudLLMProvider()
    return LocalLLMProvider()
