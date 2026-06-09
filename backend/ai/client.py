import logging
import os

logger = logging.getLogger("AIClient")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
HF_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen2.5-72B-Instruct")
HF_TIMEOUT = int(os.getenv("HF_TIMEOUT", "60"))

_client = None
_client_type = None # "groq" or "hf"
_CLIENT_INIT_FAILED = False

def get_client():
    """Lazy-initialize the AI client (Groq preferred, fallback to HF)."""
    global _client, _client_type, _CLIENT_INIT_FAILED

    if _client is not None:
        return _client, _client_type
    if _CLIENT_INIT_FAILED:
        return None, None

    # 1. Try Groq first if key is provided
    if GROQ_API_KEY and GROQ_API_KEY != "your_key_here":
        try:
            from groq import Groq
            _client = Groq(api_key=GROQ_API_KEY)
            _client_type = "groq"
            logger.info("Groq AI client initialized (model=%s)", GROQ_MODEL)
            return _client, _client_type
        except Exception as exc:
            logger.warning("Failed to initialize Groq client: %s. Falling back to HF.", exc)

    # 2. Fallback to Hugging Face
    token = os.getenv("HF_API_TOKEN", "").strip()
    if not token or token == "your_key_here":
        logger.info("No AI API keys set (GROQ_API_KEY or HF_API_TOKEN) — AI features disabled")
        _CLIENT_INIT_FAILED = True
        return None, None

    try:
        from huggingface_hub import InferenceClient
        _client = InferenceClient(token=token, timeout=HF_TIMEOUT)
        _client_type = "hf"
        logger.info("Hugging Face InferenceClient initialized (model=%s)", HF_MODEL)
        return _client, _client_type
    except Exception as exc:
        logger.warning("Failed to initialize HF client: %s", exc)
        _CLIENT_INIT_FAILED = True
        return None, None

def generate_completion(prompt: str, system_prompt: str = None, max_tokens: int = 800, temperature: float = 0.2) -> str:
    """Generates a completion using the initialized client."""
    client, ctype = get_client()
    if client is None:
        return ""
        
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        if ctype == "groq":
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return (response.choices[0].message.content or "").strip()
        else: # hf
            response = client.chat_completion(
                model=HF_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return (response.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.warning("%s generation failed: %s", ctype.upper() if ctype else "AI", exc)
        return ""

def stream_completion(prompt: str, system_prompt: str = None, max_tokens: int = 800, temperature: float = 0.2):
    """Yields a streaming completion using the initialized client."""
    client, ctype = get_client()
    if client is None:
        return
        
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        if ctype == "groq":
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            )
            for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        else: # hf
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
        logger.warning("%s streaming generation failed: %s", ctype.upper() if ctype else "AI", exc)
