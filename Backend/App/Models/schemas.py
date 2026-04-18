"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ── Request Models ──────────────────────────────────────────────

class ProcessVideoRequest(BaseModel):
    """Request to process a YouTube video."""
    url: str = Field(..., description="YouTube video URL")


class ChatRequest(BaseModel):
    """Request to chat about a processed video."""
    message: str = Field(..., description="User's question")
    video_id: str = Field(..., description="YouTube video ID")
    thread_id: Optional[str] = Field(
        default=None,
        description="Conversation thread ID for memory. Auto-generated if not provided.",
    )


# ── Response Models ─────────────────────────────────────────────

class TimestampReference(BaseModel):
    """A reference to a specific moment in the video."""
    text: str = Field(..., description="Relevant transcript text")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    url: str = Field(..., description="YouTube URL with timestamp")


class ProcessVideoResponse(BaseModel):
    """Response after processing a video."""
    video_id: str
    title: str
    chunk_count: int
    duration_formatted: str
    message: str = "Video processed successfully"


class ChatResponse(BaseModel):
    """Non-streaming chat response."""
    answer: str
    timestamps: list[TimestampReference] = []
    thread_id: str


class VideoStatusResponse(BaseModel):
    """Response for video indexing status check."""
    video_id: str
    is_indexed: bool
    chunk_count: int = 0


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None


# ── Quiz Models ─────────────────────────────────────────────

class QuizGenerateRequest(BaseModel):
    """Request to generate a quiz from a processed video."""
    video_id: str = Field(..., description="YouTube video ID")
    difficulty: str = Field(
        default="medium",
        description="Difficulty level: easy, medium, or hard",
    )
    question_types: list[str] = Field(
        default=["mcq", "short_answer", "flashcard"],
        description="Types of questions to generate",
    )
    num_questions: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of questions per type",
    )


class MCQQuestion(BaseModel):
    """A multiple-choice question."""
    question: str
    options: list[str]
    correct_answer_index: int
    explanation: str
    timestamp: Optional[str] = None
    difficulty: str


class ShortAnswerQuestion(BaseModel):
    """A short answer question."""
    question: str
    model_answer: str
    key_points: list[str]
    timestamp: Optional[str] = None
    difficulty: str


class Flashcard(BaseModel):
    """A flashcard with front and back."""
    front: str
    back: str
    timestamp: Optional[str] = None
    difficulty: str


class QuizResponse(BaseModel):
    """Response containing generated quiz data."""
    video_id: str
    difficulty: str
    mcqs: list[MCQQuestion] = []
    short_answers: list[ShortAnswerQuestion] = []
    flashcards: list[Flashcard] = []
    total_questions: int
