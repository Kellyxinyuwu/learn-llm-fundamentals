# schemas.py — Overview

`schema.py` does **not** call the LLM. It only defines the **shape** of the data and validates it.

## Where schemas.py Fits in the Big Picture

The full pipeline (which you'll build in `json_runner.py`) will look like this:

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  User asks a    │ ──▶  │  LLM returns    │ ──▶  │  We parse JSON  │
│  question       │      │  JSON text      │      │  and validate   │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                                                  │  schemas.py     │
                                                  │  QAResponse     │
                                                  │  validates the  │
                                                  │  parsed dict    │
                                                  └─────────────────┘
```

`schema.py` sits at the **last step**. When the LLM returns text, we'll parse it as JSON into a Python dict, then pass that dict to `QAResponse.model_validate(...)`. If it passes, we have a typed, validated object. If it fails, we can retry or surface an error.

---

## What Each Function Does

### `Citation` and `QAResponse` (the schema classes)

These describe the **shape** of the data we expect the LLM to return:

| Part | Purpose |
|------|---------|
| `Citation` | One piece of evidence: `source_id` + `quote` |
| `QAResponse` | The full answer: `answer` (string) + `citations` (list of `Citation`) |

They're not functions—they're **blueprints**. Later, when we call `QAResponse.model_validate(data)`, Pydantic uses these blueprints to check if `data` matches.

---

### `QAResponse.model_validate(data)`

- **Input:** A Python dict (e.g. from `json.loads()` of the LLM's raw text)
- **Output:** A `QAResponse` object if the data is valid
- **Throws:** `ValidationError` if the dict is missing fields, has wrong types, etc.

In plain English: *"Given this raw dict, does it match our schema? If yes, give me a typed object. If no, raise an error."*

---

### `result.model_dump()`

- **Input:** A Pydantic model instance (e.g. a `QAResponse` object)
- **Output:** A plain Python dict with the same data

Useful when you need to serialize or pass the validated result elsewhere (e.g. to JSON, another API, or a database).

---

## Why the Test Uses Fake Data

The `if __name__ == "__main__"` block at the bottom **does not call the LLM**. It's a unit test for the schema itself. It simulates: *"What if we already had a dict that looks like an LLM response? Does our validation work?"*

Later, in `json_runner.py`, the real flow will be: LLM returns text → we parse to dict → we validate with `QAResponse.model_validate()`. The test just verifies the validation step in isolation.

---

# llm_client.py — Overview

`llm_client.py` is the **interface to the LLM**. It sends prompts to Ollama (local models) and returns the model's text response. No API key required.

## Where llm_client.py Fits in the Big Picture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  User asks a    │ ──▶  │  llm_client.py  │ ──▶  │  LLM returns    │
│  question       │      │  call_llm()     │      │  JSON text      │
└─────────────────┘      └─────────────────┘      └─────────────────┘
        │                         │                         │
        │                         │                         ▼
        │                         │                ┌─────────────────┐
        │                         │                │  schemas.py     │
        │                         │                │  validates      │
        │                         │                └─────────────────┘
        │                         │
        ▼                         ▼
  json_runner.py          Ollama (localhost:11434)
```

`llm_client.py` sits at the **first step** of the LLM call. It takes a prompt string and returns whatever text the model generates. It does not parse or validate—that happens in `json_runner.py` with `schemas.py`.

---

## What Each Part Does

### `DEFAULT_MODEL`

- **Value:** `"llama3.2"` (or `"mistral"`, `"codellama"`, etc.)
- **Purpose:** The default Ollama model to use. Centralized so you can switch models easily.

---

### `call_llm(prompt, model, temperature)`

The main function. Sends a prompt to Ollama and returns the model's reply.

| Parameter | Type | Purpose |
|-----------|------|---------|
| `prompt` | `str` | The text to send to the model |
| `model` | `str` | Ollama model name (default: `DEFAULT_MODEL`) |
| `temperature` | `float` | Controls randomness (0.0 = deterministic, higher = more creative) |

**Returns:** `str` — The model's raw text response.

**Requires:** Ollama running (`ollama serve`) and a model pulled (`ollama pull llama3.2`).

---

### How it works internally

1. **`ollama.chat()`** — Calls the Ollama API at `localhost:11434`.
2. **`messages=[{"role": "user", "content": prompt}]`** — Uses OpenAI-style message format.
3. **`options={"temperature": temperature}`** — Passes sampling options.
4. **`resp["message"]["content"]`** — Extracts the assistant's reply from the response dict.

---

## Test block

The `if __name__ == "__main__"` block sends a simple prompt (`"What is the capital of France?"`) and prints the response. Run with:

```bash
python llm_client.py
```
