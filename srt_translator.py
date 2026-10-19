import argparse
import re
import sys
import time
from pathlib import Path

import requests
import srt


OLLAMA_URL = "http://localhost:11434/api/chat"
# DEFAULT_MODEL = "qwen3.5:2b"
DEFAULT_MODEL = "s1gnature/gemma4-uncensored-mtp:e2b-q4_k_m"

LANGUAGES = {
    "zh": "natural Simplified Chinese",
    "zh-TW": "natural Traditional Chinese",
    "ja": "natural Japanese",
    "en": "natural English",
}


def translate_batch(texts, target_language, model=DEFAULT_MODEL, retries=3):
    """
    Translate multiple subtitle texts in one request.
    The model must return one numbered translation per input line.
    """
    if not texts:
        return []

    numbered_texts = "\n".join(
        f"{i + 1}. {text.replace(chr(10), ' ')}"
        for i, text in enumerate(texts)
    )

    prompt = f"""Translate each subtitle into {target_language}.
Keep the same number of items and preserve their order.
Return ONLY the translated items, one per line, using exactly this format:
1. translated text
2. translated text
Do not add explanations or combine items.

Subtitles:
{numbered_texts}"""

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "options": {"temperature": 0.1},
    }

    last_error = None
    for attempt in range(retries):
        try:
            response = requests.post(
                OLLAMA_URL, json=payload, timeout=300
            )
            response.raise_for_status()
            content = response.json()["message"]["content"].strip()
            translations = parse_numbered_translations(content, len(texts))
            if translations is not None:
                return translations
            last_error = RuntimeError(
                "Model did not return the expected numbered list.\n"
                f"Received:\n{content}"
            )
        except (requests.RequestException, KeyError, ValueError, RuntimeError) as exc:
            last_error = exc

        if attempt < retries - 1:
            time.sleep(1.5 * (attempt + 1))

    raise RuntimeError(f"Translation failed after {retries} attempts: {last_error}")


def parse_numbered_translations(content, expected_count):
    """
    Parse lines like '1. translated text'. Return None if output is malformed.
    """
    results = {}
    for line in content.splitlines():
        match = re.match(r"^\s*(\d+)[.)]\s*(.*?)\s*$", line)
        if match:
            number = int(match.group(1))
            if 1 <= number <= expected_count:
                results[number] = match.group(2)

    if len(results) != expected_count or any(
        not results.get(i, "").strip() for i in range(1, expected_count + 1)
    ):
        return None

    return [results[i].strip() for i in range(1, expected_count + 1)]


def chunked(items, size):
    for start in range(0, len(items), size):
        yield start, items[start:start + size]


def translate_srt(
    input_path,
    output_path,
    target_language,
    model=DEFAULT_MODEL,
    batch_size=5,
):
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if input_path.resolve() == output_path.resolve():
        raise ValueError("Input and output paths must be different.")
    if batch_size < 1:
        raise ValueError("Batch size must be at least 1.")

    raw = input_path.read_text(encoding="utf-8-sig")
    subtitles = list(srt.parse(raw))

    if not subtitles:
        raise ValueError("No subtitles found in the input file.")

    # Keep empty-text entries and non-dialogue cues untouched.
    indices = [
        i for i, sub in enumerate(subtitles)
        if sub.content.strip()
    ]
    source_texts = [subtitles[i].content for i in indices]

    print(f"Loaded {len(subtitles)} subtitle entries.")
    print(f"Translating {len(source_texts)} non-empty entries into {target_language}.")
    print(f"Model: {model}")

    completed = 0
    for _, batch in chunked(source_texts, batch_size):
        translated = translate_batch(batch, target_language, model=model)
        for source_index, translated_text in zip(
            indices[completed:completed + len(batch)], translated
        ):
            subtitles[source_index].content = translated_text
        completed += len(batch)
        print(f"\rProgress: {completed}/{len(source_texts)}", end="", flush=True)

    print()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        srt.compose(subtitles),
        encoding="utf-8",
        newline="\n",
    )
    print(f"Saved translated subtitles to: {output_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description="Translate SRT subtitles using a local Ollama model."
    )
    parser.add_argument("input", help="Input .srt file")
    parser.add_argument(
        "-o", "--output",
        help="Output .srt path (default: <input>.<language>.srt)",
    )
    parser.add_argument(
        "-t", "--target",
        choices=LANGUAGES.keys(),
        default="zh",
        help="Target language: zh, zh-TW, ja, en (default: zh)",
    )
    parser.add_argument(
        "-m", "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "-b", "--batch-size",
        type=int,
        default=5,
        help="Subtitle entries per request (default: 5)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    target_language = LANGUAGES[args.target]
    output_path = Path(args.output) if args.output else input_path.with_name(
        f"{input_path.stem}.{args.target}.srt"
    )

    try:
        translate_srt(
            input_path=input_path,
            output_path=output_path,
            target_language=target_language,
            model=args.model,
            batch_size=args.batch_size,
        )
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
