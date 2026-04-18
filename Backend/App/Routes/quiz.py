"""
Quiz API routes — Generate quizzes from processed video transcripts.
"""

from fastapi import APIRouter, HTTPException

from App.Models.schemas import (
    QuizGenerateRequest,
    QuizResponse,
    MCQQuestion,
    ShortAnswerQuestion,
    Flashcard,
    ErrorResponse,
)
from App.Services.vectorstore import VectorStoreService
from App.Services.quiz_generator import generate_quiz

router = APIRouter(prefix="/api", tags=["quiz"])


@router.post(
    "/quiz/generate",
    response_model=QuizResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def generate_quiz_endpoint(request: QuizGenerateRequest):
    """
    Generate a quiz (MCQs, Short Answers, Flashcards) from a processed video.
    
    Supports difficulty levels: easy, medium, hard.
    """
    try:
        # Validate video is indexed
        vectorstore = VectorStoreService()
        if not vectorstore.is_video_indexed(request.video_id):
            raise HTTPException(
                status_code=400,
                detail="Video has not been processed yet. Please process the video first.",
            )

        # Validate difficulty
        if request.difficulty not in ("easy", "medium", "hard"):
            raise HTTPException(
                status_code=400,
                detail="Difficulty must be 'easy', 'medium', or 'hard'.",
            )

        # Validate question types
        valid_types = {"mcq", "short_answer", "flashcard"}
        for qt in request.question_types:
            if qt not in valid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid question type '{qt}'. Must be one of: {valid_types}",
                )

        # Generate the quiz
        result = generate_quiz(
            video_id=request.video_id,
            difficulty=request.difficulty,
            question_types=request.question_types,
            num_questions=request.num_questions,
        )

        return QuizResponse(
            video_id=request.video_id,
            difficulty=request.difficulty,
            mcqs=[MCQQuestion(**q) for q in result["mcqs"]],
            short_answers=[ShortAnswerQuestion(**q) for q in result["short_answers"]],
            flashcards=[Flashcard(**q) for q in result["flashcards"]],
            total_questions=result["total_questions"],
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Quiz] Error generating quiz: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate quiz: {str(e)}",
        )
