
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
# MODEL = "qwen3.5:2b"
MODEL = "s1gnature/gemma4-uncensored-mtp:e2b-q4_k_m"


def translate_text(text, target_language="Simplified Chinese"):
    prompt = (
        f"Translate the following subtitle into natural {target_language}.\n"
        "Preserve the original meaning, tone, and implied emotion.\n"
        "Do not explain, add information, or include quotation marks.\n"
        "Return only the translated subtitle text.\n\n"
        f"Subtitle:\n{text}"
    )

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.1
        }
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=300
    )
    response.raise_for_status()

    data = response.json()
    return data["message"]["content"].strip()


if __name__ == "__main__":
    original = "I told you not to come here alone."

    translated = translate_text(original)

    print("Original:   ", original)
    print("Translated:", translated)
