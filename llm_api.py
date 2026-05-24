import os
import requests

# 1️⃣ Correct: environment variable NAME
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# 2️⃣ Correct: chat completions endpoint
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def call_llm(prompt: str, history=None) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = []
    if history:
        for msg in history[-12:]:
            role = msg.get("role")
            content = msg.get("content", "")
            if role in {"user", "assistant", "system"} and content:
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.7
    }

    response = requests.post(
        GROQ_API_URL,
        headers=headers,
        json=payload,
        timeout=60
    )
    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]
