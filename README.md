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

**Why Ollama instead of OpenAI or Bedrock?** For learning and prototyping, Ollama runs models locally on your machine—no API keys, no usage costs, and no network calls. You can iterate quickly and experiment with prompts and schemas without hitting rate limits or billing. When you're ready for production, the same patterns (prompt → response → validate) apply to cloud providers: swap in OpenAI, Bedrock, or Azure OpenAI by changing the client implementation while keeping `json_runner.py` and `schemas.py` unchanged.

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

---

# json_runner.py — Overview

`json_runner.py` is the **orchestrator**. It ties together `llm_client.py` and `schemas.py`: it builds the prompt, calls the LLM, parses the JSON response, validates it against the schema, and retries if parsing or validation fails. This gives you reliable structured outputs suitable for production.

## Where json_runner.py Fits in the Big Picture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  main()         │ ──▶ │  ask_llm_for_   │ ──▶ │  call_llm()     │ ──▶ │  LLM returns    │
│  builds prompt  │     │  json()         │     │  (llm_client)   │     │  JSON text      │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
         │                        │                        │                        │
         │                        │                        │                        ▼
         │                        │                        │               ┌─────────────────┐
         │                        │                        │               │  _extract_json  │
         │                        │                        │               │  json.loads     │
         │                        │                        │               │  model_validate │
         │                        │                        │               └─────────────────┘
         │                        │                        │                        │
         │                        ▼                        │                        ▼
         │               Retry on failure? ─────────────────┘               QAResponse ✓
         └──────────────────────────────────────────────────────────────────────────────
```

`json_runner.py` runs the full loop: prompt → call LLM → parse → validate → retry if needed → return typed result.

---

## What Each Part Does

### Imports and `TypeVar`

- **`json`** — Parse the LLM's raw text into a Python dict.
- **`re`** — Extract JSON from markdown code blocks (models often wrap output in \`\`\`json ... \`\`\`).
- **`TypeVar("T", bound=BaseModel)`** — Makes `ask_llm_for_json` generic: it can validate against any Pydantic model (e.g. `QAResponse` or a future schema).
- **`ValidationError`** — Caught when Pydantic validation fails so we can retry with feedback.

---

### `SYSTEM_INSTRUCTIONS` and `MAX_RETRIES`

- **`SYSTEM_INSTRUCTIONS`** — Tells the LLM its role, the exact JSON schema to return, and the rules (concise answer, at least one citation, no markdown). Clear instructions improve reliability.
- **`MAX_RETRIES`** — How many times to retry when parsing or validation fails (default 3). Avoids infinite loops when the model keeps returning invalid JSON.

---

### `_extract_json(text)`

**Purpose:** LLMs often wrap JSON in markdown code blocks, which break `json.loads()`. This helper pulls out the JSON string.

**Logic:**
1. Strip whitespace from the input.
2. If `\`\`\`json` appears, use regex to extract the content between `\`\`\`json` and `\`\`\``.
3. If only `\`\`\`` appears (no `json` tag), try extracting content between plain `\`\`\`` blocks.
4. If neither matches, return the original text (assume it's raw JSON).

**Returns:** A string that should be valid JSON (or close to it).

---

### `ask_llm_for_json(prompt, schema_cls, model, max_retries)`

**Purpose:** The core function. Calls the LLM, parses JSON, validates against the schema, and retries on failure with error feedback.

**Flow:**
1. **Loop** up to `max_retries` times.
2. **Call** `call_llm(current_prompt)` to get raw text.
3. **Extract** JSON with `_extract_json(raw)`.
4. **Try:** `json.loads()` → `schema_cls.model_validate(data)`.
5. **Success** → return the validated Pydantic object.
6. **Failure** → catch `JSONDecodeError` or `ValidationError`, store the error message, and if retries remain, append to the prompt: *"Your previous response was invalid: {error}. Please fix the JSON."* Then loop again.
7. **Exhausted retries** → raise `ValueError` with the last error.

**Banking-grade idea:** Sending the error back to the model gives it a chance to fix the output. Many failures (trailing commas, extra text) can be corrected on retry.

---

### `main()`

**Purpose:** CLI entry point. Parses arguments, builds the prompt, calls `ask_llm_for_json`, and prints the result.

**Arguments:**
| Flag | Purpose |
|------|---------|
| `--context` | Context documents (for RAG-style Q&A) |
| `--question` | The question to answer |
| `--model` | Ollama model name (default: llama3.2) |
| `--demo` | Use built-in example context and question |

**Logic:**
1. Parse CLI args with `argparse`.
2. If `--demo` or no context/question, use hardcoded financial example.
3. Build prompt: `SYSTEM_INSTRUCTIONS` + context + question + "Return ONLY JSON."
4. Call `ask_llm_for_json(user_prompt, QAResponse, model=args.model)`.
5. Print `result.model_dump_json(indent=2)`.

---

## How to run

```bash
# Demo mode (example context + question)
python json_runner.py --demo

# Custom context and question
python json_runner.py --context "Document: ..." --question "What is..."
```
