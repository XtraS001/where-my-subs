
from pathlib import Path
from typing import Callable

from faster_whisper import WhisperModel


def format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format."""
    total_ms = max(0, round(seconds * 1000))

    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, milliseconds = divmod(remainder, 1000)

    return (
        f"{hours:02}:{minutes:02}:"
        f"{secs:02},{milliseconds:03}"
    )


def get_output_path(audio_path: Path) -> Path:
    """Choose an output filename without overwriting an existing file."""
    output_path = audio_path.with_suffix(".srt")

    counter = 2
    while output_path.exists():
        output_path = audio_path.with_name(
            f"{audio_path.stem}_{counter}.srt"
        )
        counter += 1

    return output_path


def transcribe_to_srt(
    audio_path: Path,
    model_name: str = "small",
    device: str = "cpu",
    compute_type: str = "int8",
    progress_callback: Callable[[int], None] | None = None,
) -> Path:
    audio_path = Path(audio_path)

    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Load the selected Whisper model.
    model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
    )

    # Transcription is lazy: segments are generated as we iterate.
    segments, info = model.transcribe(
        str(audio_path),
        beam_size=5,
        vad_filter=True,
    )

    output_path = get_output_path(audio_path)
    count = 0

    try:
        with output_path.open(
            "w", encoding="utf-8-sig", newline="\n"
        ) as output:
            for count, segment in enumerate(segments, start=1):
                start = format_timestamp(segment.start)
                end = format_timestamp(segment.end)
                text = segment.text.strip()

                output.write(
                    f"{count}\n"
                    f"{start} --> {end}\n"
                    f"{text}\n\n"
                )

                if progress_callback:
                    progress_callback(count)

        if count == 0:
            raise RuntimeError(
                f"No speech segments detected. "
                f"Detected language: {info.language}"
            )

    except Exception:
        output_path.unlink(missing_ok=True)
        raise

    return output_path
