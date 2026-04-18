"""
YouTube transcript extraction service.
Handles URL parsing, transcript fetching, and video metadata retrieval.
"""

import re
import time
import urllib.request
import json
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> str:
    """
    Extract video ID from various YouTube URL formats.

    Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/shorts/VIDEO_ID
        - Raw video ID string
    """
    url = url.strip()

    # Try parsing as a proper URL first (handles query params correctly)
    try:
        parsed = urlparse(url)
        
        # youtube.com/watch?v=ID
        if parsed.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
            if parsed.path == '/watch':
                qs = parse_qs(parsed.query)
                if 'v' in qs:
                    vid = qs['v'][0]
                    if len(vid) == 11:
                        return vid
            # /embed/ID or /shorts/ID
            for prefix in ('/embed/', '/shorts/', '/v/'):
                if parsed.path.startswith(prefix):
                    vid = parsed.path[len(prefix):][:11]
                    if len(vid) == 11:
                        return vid

        # youtu.be/ID
        if parsed.hostname == 'youtu.be':
            vid = parsed.path.lstrip('/')[:11]
            if len(vid) == 11:
                return vid
    except Exception:
        pass

    # Fallback: regex patterns
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # If no pattern matches, check if the input itself is a valid video ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url

    raise ValueError(
        f"Could not extract video ID from URL. "
        "Please provide a valid YouTube URL (e.g., https://youtube.com/watch?v=...) "
        "or an 11-character video ID."
    )


def get_transcript(video_id: str, max_retries: int = 2) -> list[dict]:
    """
    Fetch transcript segments for a YouTube video.

    Strategy:
        1. Try YouTube's built-in captions (fast, free)
        2. If unavailable, fallback to Whisper AI speech-to-text via Groq API

    Returns:
        List of dicts with keys: 'text', 'start', 'duration'
        Example: [{'text': 'Hello world', 'start': 0.0, 'duration': 3.2}, ...]
    """
    # ── Step 1: Try YouTube captions first ──
    needs_whisper = False
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            api = YouTubeTranscriptApi()

            # Try fetching: first default, then list all available and pick one
            transcript = None
            try:
                transcript = api.fetch(video_id)
            except Exception as lang_err:
                err_str = str(lang_err)
                if "No transcripts were found" in err_str or "language codes" in err_str:
                    # English not available — try listing and fetching any available language
                    print(f"[Transcript] English captions not found. Trying other languages...")
                    try:
                        transcript_list = api.list(video_id)
                        # Try to find any transcript (manual or auto-generated)
                        available = list(transcript_list)
                        if available:
                            first_lang = available[0]
                            lang_code = first_lang.language_code
                            print(f"[Transcript] Found transcript in: {first_lang.language} ({lang_code})")
                            transcript = api.fetch(video_id, languages=[lang_code])
                        else:
                            raise ValueError("No transcripts available in any language.")
                    except Exception as list_err:
                        if "No transcripts" in str(list_err):
                            raise list_err
                        raise
                else:
                    raise

            raw_data = transcript.to_raw_data()

            if not raw_data:
                raise ValueError("Transcript returned empty data.")

            print(f"[Transcript] ✓ Fetched {len(raw_data)} segments via YouTube captions")
            return raw_data

        except Exception as e:
            last_error = e
            error_msg = str(e)
            print(f"[Transcript] YouTube captions attempt {attempt + 1}/{max_retries + 1} failed: {error_msg}")

            # These errors mean captions don't exist → use Whisper
            if any(kw in error_msg for kw in [
                "TranscriptsDisabled", "NoTranscriptFound",
                "No transcripts", "no element found",
            ]):
                needs_whisper = True
                break

            # Don't fallback for these errors
            if "VideoUnavailable" in error_msg:
                raise ValueError(
                    "This video is unavailable. "
                    "It may be private, deleted, or region-restricted."
                )

            if "Too Many Requests" in error_msg:
                raise ValueError(
                    "YouTube is rate-limiting requests. Please wait and try again."
                )

            # Wait before retrying
            if attempt < max_retries:
                time.sleep(1)
            else:
                # Exhausted retries → try Whisper as last resort
                needs_whisper = True

    # ── Step 2: Fallback to Whisper AI transcription ──
    if needs_whisper:
        print(f"[Transcript] No YouTube captions available. Falling back to Whisper AI...")
        try:
            from App.Services.whisper_fallback import transcribe_video_fallback
            segments = transcribe_video_fallback(video_id)
            if segments:
                print(f"[Transcript] ✓ Whisper transcribed {len(segments)} segments")
                return segments
        except Exception as whisper_err:
            print(f"[Transcript] Whisper fallback also failed: {whisper_err}")
            raise ValueError(
                f"No YouTube captions found, and Whisper transcription failed: {whisper_err}. "
                "Please ensure FFmpeg is installed for audio processing, or try a video with captions."
            )

    if "VideoUnavailable" in str(last_error):
        raise ValueError(
            "This video is unavailable. "
            "It may be private, deleted, or region-restricted."
        )

    if "no element found" in error_msg or "xml" in error_msg.lower():
        raise ValueError(
            "Could not fetch transcript — YouTube returned an empty response. "
            "This video may not have captions available, or YouTube may be "
            "temporarily blocking requests. Please try again in a moment, "
            "or try a different video."
        )

    if "Too Many Requests" in error_msg:
        raise ValueError(
            "YouTube is rate-limiting requests. Please wait a minute and try again."
        )

    raise ValueError(f"Failed to fetch transcript: {error_msg}")


def get_video_metadata(video_id: str) -> dict:
    """
    Fetch basic video metadata using YouTube's oEmbed API (no API key needed).

    Returns:
        Dict with 'title', 'author', 'thumbnail_url'
    """
    oembed_url = (
        f"https://www.youtube.com/oembed"
        f"?url=https://www.youtube.com/watch?v={video_id}"
        f"&format=json"
    )

    try:
        req = urllib.request.Request(
            oembed_url,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return {
                "title": data.get("title", "Unknown Title"),
                "author": data.get("author_name", "Unknown Author"),
                "thumbnail_url": data.get("thumbnail_url", ""),
            }
    except Exception:
        return {
            "title": f"Video {video_id}",
            "author": "Unknown",
            "thumbnail_url": "",
        }


def format_duration(seconds: float) -> str:
    """Format seconds into mm:ss or hh:mm:ss string."""
    total = int(seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
