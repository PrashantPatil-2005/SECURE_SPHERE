# AI Narration Engine

## Model

- Primary: Groq `llama-3.1-8b-instant` (`GROQ_MODEL` env)
- Fallback: Hugging Face `Qwen/Qwen2.5-72B-Instruct`

## Flow

```
Incident created → _narrate_and_save() [async thread]
  → narrator.generate_narrative(incident, kill_chain_steps, service_path)
  → generate_completion(KILL_CHAIN_NARRATIVE_PROMPT + context)
  → persist to kill_chains.narrative

Live commentary (15s loop):
  → ai_commentary_loop() → Redis ai_thought_stream

API:
  POST /api/ai/chat
  GET  /api/ai/stream
  GET  /api/ai/report/{incident_id}
```

## Prompts

Defined in `backend/ai/prompts.py`. Service-path context block included in kill-chain narrative prompt.
