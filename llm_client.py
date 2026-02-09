import ollama

DEFAULT_MODEL = "llama3.2"  # or "mistral", "codellama", etc.

def call_llm(prompt: str, model: str = DEFAULT_MODEL, temperature: float = 0.1,) -> str:
    """
    Call Ollama chat completion. Returns the model's text response.
    Requires Ollama running: ollama serve (and a model: ollama pull llama3.2)
    """
    resp = ollama.chat(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    options={"temperature": temperature},
    )
    return resp["message"]["content"]




if __name__ == "__main__":
    prompt = "What is the capital of France?"
    response = call_llm(prompt)
    print(response)

