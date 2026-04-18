"""
Time-based transcript chunking service.
Splits transcript segments into larger chunks while preserving timestamp metadata.
"""

from dataclasses import dataclass, asdict


@dataclass
class TranscriptChunk:
    """A chunk of transcript text with timestamp boundaries."""
    text: str
    start_time: float
    end_time: float
    video_id: str
    chunk_index: int

    def to_dict(self) -> dict:
        return asdict(self)


def chunk_transcript(
    segments: list[dict],
    video_id: str,
    chunk_seconds: int = 60,
) -> list[TranscriptChunk]:
    """
    Group transcript segments into time-based chunks.

    Each chunk spans approximately `chunk_seconds` seconds and preserves
    the start/end timestamps for precise video referencing.

    Args:
        segments: Raw transcript segments [{'text', 'start', 'duration'}, ...]
        video_id: YouTube video ID
        chunk_seconds: Target chunk duration in seconds (default: 60)

    Returns:
        List of TranscriptChunk objects
    """
    if not segments:
        return []

    chunks: list[TranscriptChunk] = []
    current_texts: list[str] = []
    chunk_start_time: float = segments[0]["start"]
    chunk_index = 0

    for segment in segments:
        seg_start = segment["start"]
        seg_text = segment["text"].strip()
        seg_duration = segment.get("duration", 0)

        if not seg_text:
            continue

        # Check if adding this segment would exceed the chunk time window
        elapsed = seg_start - chunk_start_time

        if elapsed >= chunk_seconds and current_texts:
            # Finalize current chunk
            chunk_end = seg_start
            combined_text = " ".join(current_texts)
            combined_text = _clean_text(combined_text)

            chunks.append(TranscriptChunk(
                text=combined_text,
                start_time=chunk_start_time,
                end_time=chunk_end,
                video_id=video_id,
                chunk_index=chunk_index,
            ))

            # Start new chunk
            current_texts = []
            chunk_start_time = seg_start
            chunk_index += 1

        current_texts.append(seg_text)

    # Don't forget the last chunk
    if current_texts:
        last_seg = segments[-1]
        chunk_end = last_seg["start"] + last_seg.get("duration", 0)
        combined_text = " ".join(current_texts)
        combined_text = _clean_text(combined_text)

        chunks.append(TranscriptChunk(
            text=combined_text,
            start_time=chunk_start_time,
            end_time=chunk_end,
            video_id=video_id,
            chunk_index=chunk_index,
        ))

    return chunks


def _clean_text(text: str) -> str:
    """Clean up transcript text: remove excessive whitespace and common artifacts."""
    import re

    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)

    # Remove common auto-caption artifacts
    text = re.sub(r'\[Music\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[Applause\]', '', text, flags=re.IGNORECASE)

    return text.strip()
