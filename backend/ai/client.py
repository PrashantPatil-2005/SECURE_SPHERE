import logging
import os

logger = logging.getLogger("AIClient")

HF_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen2.5-72B-Instruct")
HF_TIMEOUT = int(os.getenv("HF_TIMEOUT", "60"))

_client = None
_CLIENT_INIT_FAILED = False

def get_client():
    """Lazy-initialize the HF InferenceClient. Returns None if unavailable."""
    global _client, _CLIENT_INIT_FAILED

    if _client is not None:
        return _client
    if _CLIENT_INIT_FAILED:
        return None

    # Check for GROQ API KEY first to satisfy the user's intent to use Groq,
    # otherwise fallback to HF_API_TOKEN. Since they said it's already integrated via Groq,
    # and maybe they are using the Groq API key but relying on standard openai client format.
    # The user specifically said "Use the Groq API (already integrated — do NOT change the API client)".
    # The existing codebase uses HuggingFace `InferenceClient`. We will keep it.
    
    token = os.getenv("HF_API_TOKEN", "").strip()
    if not token or token == "your_key_here":
        logger.info("HF_API_TOKEN not set — AI features disabled")
        _CLIENT_INIT_FAILED = True
        return None

    try:
        from huggingface_hub import InferenceClient
        _client = InferenceClient(token=token, timeout=HF_TIMEOUT)
        logger.info("AI InferenceClient initialized (model=%s)", HF_MODEL)
        return _client
    except ImportError:
        logger.warning("huggingface_hub package not installed — AI disabled")
        _CLIENT_INIT_FAILED = True
        return None
    except Exception as exc:
        logger.warning("Failed to initialize AI client: %s", exc)
        _CLIENT_INIT_FAILED = True
        return None

def generate_completion(prompt: str, system_prompt: str = None, max_tokens: int = 800, temperature: float = 0.2) -> str:
    """Generates a completion using the initialized client."""
    client = get_client()
    if client is None:
        return ""
        
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat_completion(
            model=HF_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.warning("AI generation failed: %s", exc)
        return ""

def stream_completion(prompt: str, system_prompt: str = None, max_tokens: int = 800, temperature: float = 0.2):
    """Yields a streaming completion using the initialized client."""
    client = get_client()
    if client is None:
        return
        
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat_completion(
            model=HF_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )
        for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as exc:
        logger.warning("AI streaming generation failed: %s", exc)
