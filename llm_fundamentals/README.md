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
