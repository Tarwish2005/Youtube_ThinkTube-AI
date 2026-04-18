"""
Whisper-based audio transcription fallback.
Uses Groq's Whisper API (via official groq SDK) to transcribe YouTube video audio
when YouTube captions/transcripts are not available.
"""

import os
from App.Config.settings import get_settings


def download_audio(video_id: str, output_dir: str) -> str:
    """
    Download audio from a YouTube video using yt-dlp.
    Returns path to the downloaded audio file.
    """
    import yt_dlp

    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, f"{video_id}.%(ext)s")
    url = f"https://www.youtube.com/watch?v={video_id}"

    # Try with FFmpeg audio extraction first
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '64',
        }],
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }

    try:
        print(f"[Whisper] Downloading audio for {video_id} (with FFmpeg)...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        if "ffmpeg" in str(e).lower() or "ffprobe" in str(e).lower() or "Postprocessing" in str(e):
            # FFmpeg not installed — download raw audio instead
            print(f"[Whisper] FFmpeg not available, downloading raw audio...")
            ydl_opts_raw = {
                'format': 'worstaudio[filesize<25M]/worstaudio',
                'outtmpl': output_template,
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts_raw) as ydl:
                ydl.download([url])
        else:
            raise ValueError(f"Failed to download audio: {e}")

    # Find the downloaded file
    for fname in os.listdir(output_dir):
        if fname.startswith(video_id):
            fpath = os.path.join(output_dir, fname)
            size_mb = os.path.getsize(fpath) / (1024 * 1024)
            print(f"[Whisper] Downloaded: {fname} ({size_mb:.1f} MB)")
            if size_mb > 25:
                os.remove(fpath)
                raise ValueError(
                    f"Audio is {size_mb:.1f} MB — exceeds Groq Whisper's 25MB limit. "
                    "Try a shorter video (under ~2 hours)."
                )
            return fpath

    raise FileNotFoundError(f"Audio file not found after download for video: {video_id}")


def transcribe_with_groq_whisper(audio_path: str) -> list[dict]:
    """
    Transcribe audio using Groq's Whisper API via the official groq SDK.
    Returns list of segment dicts: [{'text', 'start', 'duration'}, ...]
    """
    from groq import Groq

    settings = get_settings()
    api_key = settings.GROQ_API_KEY

    if not api_key or api_key == "your_groq_api_key_here":
        raise ValueError("GROQ_API_KEY is not set. Please add it to your .env file.")

    print(f"[Whisper] Sending audio to Groq Whisper API...")
    client = Groq(api_key=api_key)

    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            file=(os.path.basename(audio_path), audio_file),
            model="whisper-large-v3",
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    # Parse the response segments
    segments = []
    if hasattr(response, "segments") and response.segments:
        for seg in response.segments:
            start = getattr(seg, "start", 0.0)
            end = getattr(seg, "end", 0.0)
            text = getattr(seg, "text", "").strip()
            if text:
                segments.append({
                    "text": text,
                    "start": float(start),
                    "duration": float(end) - float(start),
                })
    elif hasattr(response, "text") and response.text:
        # No segment timestamps — wrap full text as single segment
        segments.append({
            "text": response.text.strip(),
            "start": 0.0,
            "duration": 0.0,
        })

    print(f"[Whisper] ✓ Transcribed {len(segments)} segments via Groq Whisper")
    return segments


def transcribe_video_fallback(video_id: str) -> list[dict]:
    """
    Full pipeline: download audio → transcribe with Whisper.
    Cleans up the audio file after transcription.
    """
    temp_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        ))),
        "data", "audio_temp"
    )

    audio_path = None
    try:
        audio_path = download_audio(video_id, temp_dir)
        segments = transcribe_with_groq_whisper(audio_path)
        return segments
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                print(f"[Whisper] Cleaned up: {audio_path}")
            except Exception:
                pass
