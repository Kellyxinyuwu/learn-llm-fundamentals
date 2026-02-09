import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from llm_client import call_llm
from schemas import QAResponse

T = TypeVar("T", bound=BaseModel)


SYSTEM_INSTRUCTIONS = """You are a financial analysis assistant.
Read the given context and answer the user's question.
You MUST respond ONLY as a JSON object matching this schema:
{
  "answer": "string",
  "citations": [
    {
      "source_id": "string",
      "quote": "string"
    }
  ]
}
- 'answer' should be concise but complete.
- 'citations' should include at least 1 exact quote from the context.
Return ONLY valid JSON. No markdown, no explanation, no code block."""

MAX_RETRIES = 3


def _extract_json(text: str) -> str:
    """Try to extract JSON from model output (handles markdown code blocks)."""
    text = text.strip()
    if "```json" in text:
        match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
        if match:
            return match.group(1).strip()
    if "```" in text:
        match = re.search(r"```\s*([\s\S]*?)\s*```", text)
        if match:
            return match.group(1).strip()
    return text


def ask_llm_for_json(
    prompt: str,
    schema_cls: type[T],
    model: str = "llama3.2",
    max_retries: int = MAX_RETRIES,
) -> T:
    """
    Call LLM, parse response as JSON, validate against schema.
    On failure: send error back to model and retry.
    """
    current_prompt = prompt
    last_error: str | None = None

    for attempt in range(max_retries):
        raw = call_llm(current_prompt, model=model)
        json_str = _extract_json(raw)

        try:
            data = json.loads(json_str)
            return schema_cls.model_validate(data)
        except json.JSONDecodeError as e:
            last_error = f"JSON decode error: {e}"
        except ValidationError as e:
            last_error = f"Schema validation error: {e}"

        if attempt < max_retries - 1:
            current_prompt = f"""{current_prompt}
            ---
            Your previous response was invalid:
            {last_error}

            Please fix the JSON and return ONLY valid JSON matching the schema. No other text.
            """
        else:
            raise ValueError(f"Failed after {max_retries} attempts. Last error: {last_error}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ask LLM for JSON with retry")
    parser.add_argument("--context", type=str, help="Context documents for the question")
    parser.add_argument("--question", type=str, help="Question to answer")
    parser.add_argument("--model", type=str, default="llama3.2", help="Ollama model name")
    parser.add_argument("--demo", action="store_true", help="Run with example context/question")
    args = parser.parse_args()

    if args.demo or (not args.context and not args.question):
        context = """
Document A (id: doc_001): The company reported revenue of $50M in Q3, up 15% YoY.
Document B (id: doc_002): Operating margin improved to 22% due to cost savings.
Document C (id: doc_003): CEO stated: "We expect strong growth in fiscal 2025."
"""
        question = "What was the revenue and growth in Q3?"
    else:
        context = args.context or ""
        question = args.question or ""

    if not question:
        parser.error("Provide --question or use --demo")

    user_prompt = f"""{SYSTEM_INSTRUCTIONS}

Context:
{context}

Question:
{question}

Return ONLY JSON."""

    result = ask_llm_for_json(user_prompt, QAResponse, model=args.model)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
