"""
Chat API routes for video processing and Q&A.
"""

import json
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from App.Models.schemas import (
    ProcessVideoRequest,
    ProcessVideoResponse,
    ChatRequest,
    ChatResponse,
    TimestampReference,
    VideoStatusResponse,
    ErrorResponse,
)
from App.Services.transcript import (
    extract_video_id,
    get_transcript,
    get_video_metadata,
    format_duration,
)
from App.Services.chunker import chunk_transcript
from App.Services.vectorstore import VectorStoreService
from App.Services.agent import chat, stream_chat
from App.Config.settings import get_settings

router = APIRouter(prefix="/api", tags=["chat"])


@router.post(
    "/process",
    response_model=ProcessVideoResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def process_video(request: ProcessVideoRequest):
    """
    Process a YouTube video: extract transcript, chunk, embed, and index.
    """
    try:
        # 1. Extract video ID
        video_id = extract_video_id(request.url)

        # 2. Check if already indexed
        vectorstore = VectorStoreService()
        if vectorstore.is_video_indexed(video_id):
            metadata = get_video_metadata(video_id)
            chunk_count = vectorstore.get_chunk_count(video_id)
            return ProcessVideoResponse(
                video_id=video_id,
                title=metadata["title"],
                chunk_count=chunk_count,
                duration_formatted="Already processed",
                message="Video was already processed. You can start chatting!",
            )

        # 3. Fetch transcript
        print(f"[Process] Fetching transcript for {video_id}...")
        segments = get_transcript(video_id)

        if not segments:
            raise HTTPException(
                status_code=400,
                detail="No transcript segments found for this video.",
            )

        # 4. Get video metadata
        metadata = get_video_metadata(video_id)

        # 5. Chunk the transcript
        settings = get_settings()
        chunks = chunk_transcript(
            segments=segments,
            video_id=video_id,
            chunk_seconds=settings.CHUNK_SECONDS,
        )

        # 6. Calculate total duration
        last_segment = segments[-1]
        total_duration = last_segment["start"] + last_segment.get("duration", 0)
        duration_str = format_duration(total_duration)

        # 7. Index in vector store
        print(f"[Process] Indexing {len(chunks)} chunks...")
        chunk_count = vectorstore.index_video(video_id, chunks)

        print(f"[Process] ✓ Video '{metadata['title']}' processed successfully.")

        return ProcessVideoResponse(
            video_id=video_id,
            title=metadata["title"],
            chunk_count=chunk_count,
            duration_formatted=duration_str,
            message="Video processed successfully! You can now ask questions.",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[Process] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process video: {str(e)}",
        )


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Chat with the RAG agent about a processed video.
    Returns a streaming SSE response.
    """
    try:
        # Validate video is indexed
        vectorstore = VectorStoreService()
        if not vectorstore.is_video_indexed(request.video_id):
            raise HTTPException(
                status_code=400,
                detail="Video has not been processed yet. Please process the video first.",
            )

        thread_id = request.thread_id or str(uuid.uuid4())

        # Return SSE streaming response
        async def event_stream():
            try:
                for event_data in stream_chat(
                    message=request.message,
                    video_id=request.video_id,
                    thread_id=thread_id,
                ):
                    yield f"data: {event_data}\n\n"
            except Exception as e:
                error_event = json.dumps({
                    "type": "error",
                    "message": str(e),
                })
                yield f"data: {error_event}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/chat/sync",
    response_model=ChatResponse,
)
async def chat_sync_endpoint(request: ChatRequest):
    """
    Non-streaming chat endpoint. Returns the complete response at once.
    Useful for testing or when SSE is not supported.
    """
    try:
        vectorstore = VectorStoreService()
        if not vectorstore.is_video_indexed(request.video_id):
            raise HTTPException(
                status_code=400,
                detail="Video has not been processed yet.",
            )

        thread_id = request.thread_id or str(uuid.uuid4())

        result = await chat(
            message=request.message,
            video_id=request.video_id,
            thread_id=thread_id,
        )

        return ChatResponse(
            answer=result["answer"],
            timestamps=[
                TimestampReference(
                    text=ts["text"],
                    start_time=ts["start_time"],
                    end_time=ts["end_time"],
                    url=ts["url"],
                )
                for ts in result["timestamps"]
            ],
            thread_id=result["thread_id"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/video/{video_id}/status",
    response_model=VideoStatusResponse,
)
async def video_status(video_id: str):
    """Check if a video has been indexed."""
    vectorstore = VectorStoreService()
    is_indexed = vectorstore.is_video_indexed(video_id)
    chunk_count = vectorstore.get_chunk_count(video_id) if is_indexed else 0

    return VideoStatusResponse(
        video_id=video_id,
        is_indexed=is_indexed,
        chunk_count=chunk_count,
    )


@router.delete("/video/{video_id}")
async def delete_video(video_id: str):
    """Delete a video's indexed data."""
    vectorstore = VectorStoreService()
    success = vectorstore.delete_video(video_id)

    if success:
        return {"message": f"Video {video_id} data deleted successfully."}
    raise HTTPException(status_code=404, detail="Video not found in index.")
