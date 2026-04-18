"""
Quiz Generator Service — Generates MCQs, Short Answers, and Flashcards
from YouTube video transcripts using the Groq LLM.

Supports three difficulty levels:
  - Easy: Recall & definition questions
  - Medium: Understanding & application questions
  - Hard: Analysis, comparison & critical thinking questions
"""

import json
import re
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from App.Config.settings import get_settings
from App.Services.vectorstore import VectorStoreService
from App.Services.transcript import format_duration


# ═══════════════════════════════════════════════════════════════
# Difficulty Prompts
# ═══════════════════════════════════════════════════════════════

DIFFICULTY_GUIDELINES = {
    "easy": """
DIFFICULTY: EASY
- Ask straightforward recall and definition questions.
- Questions should test basic understanding and memory.
- Options in MCQs should be clearly distinguishable.
- Flashcards should cover key terms and basic definitions.
- Short answers should require 1-2 sentence responses.
""",
    "medium": """
DIFFICULTY: MEDIUM
- Ask questions that test understanding and application of concepts.
- Questions should require connecting ideas from different parts.
- MCQ distractors should be plausible but clearly wrong upon reflection.
- Flashcards should cover relationships between concepts.
- Short answers should require explanation, not just recall.
""",
    "hard": """
DIFFICULTY: HARD
- Ask questions involving analysis, comparison, and critical thinking.
- Questions should require synthesizing information from multiple sections.
- MCQ distractors should be very plausible, testing deep understanding.
- Flashcards should cover nuanced distinctions and edge cases.
- Short answers should require multi-step reasoning or evaluation.
""",
}


# ═══════════════════════════════════════════════════════════════
# Quiz Generation Prompt
# ═══════════════════════════════════════════════════════════════

QUIZ_PROMPT = """You are an expert educational quiz generator. Generate quiz questions 
from the following video transcript content.

{difficulty_guidelines}

TRANSCRIPT CONTENT:
{context}

INSTRUCTIONS:
Generate exactly the requested questions based on the transcript above.
{type_instructions}

CRITICAL: You MUST respond with ONLY valid JSON. No markdown, no code fences, no explanation.
Use this exact structure:

{{
  "mcqs": [
    {{
      "question": "What is...?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer_index": 0,
      "explanation": "Brief explanation of why this is correct",
      "timestamp": "MM:SS",
      "difficulty": "{difficulty}"
    }}
  ],
  "short_answers": [
    {{
      "question": "Explain how...",
      "model_answer": "A complete model answer...",
      "key_points": ["Key point 1", "Key point 2", "Key point 3"],
      "timestamp": "MM:SS",
      "difficulty": "{difficulty}"
    }}
  ],
  "flashcards": [
    {{
      "front": "Term or question",
      "back": "Definition or answer",
      "timestamp": "MM:SS",
      "difficulty": "{difficulty}"
    }}
  ]
}}

Only include the question types that were requested. If a type is not requested, 
use an empty array for it.

Respond with ONLY the JSON object, nothing else."""


# ═══════════════════════════════════════════════════════════════
# LLM Setup
# ═══════════════════════════════════════════════════════════════

def _get_llm():
    settings = get_settings()
    return ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.7,  # Slightly higher for creative question generation
        max_tokens=4096,
    )


# ═══════════════════════════════════════════════════════════════
# Main Generator
# ═══════════════════════════════════════════════════════════════

def _get_full_transcript_context(video_id: str, max_chunks: int = 20) -> str:
    """
    Retrieve a broad set of transcript chunks to give the LLM
    enough context for meaningful quiz generation.
    """
    vectorstore = VectorStoreService()

    # Use a broad query to get diverse chunks across the video
    broad_queries = [
        "main topics and key concepts discussed",
        "important definitions and explanations",
        "examples and demonstrations shown",
    ]

    all_chunks = {}
    for query in broad_queries:
        results = vectorstore.search(video_id=video_id, query=query, k=8)
        for doc in results:
            chunk_key = doc.get("chunk_index", doc["start_time"])
            if chunk_key not in all_chunks:
                all_chunks[chunk_key] = doc

    # Sort by time order and limit
    sorted_chunks = sorted(all_chunks.values(), key=lambda x: x["start_time"])
    selected = sorted_chunks[:max_chunks]

    # Build context string
    context_parts = []
    for doc in selected:
        start_fmt = format_duration(doc["start_time"])
        end_fmt = format_duration(doc["end_time"])
        context_parts.append(f"[{start_fmt} - {end_fmt}]: {doc['text']}")

    return "\n\n".join(context_parts)


def generate_quiz(
    video_id: str,
    difficulty: str = "medium",
    question_types: list[str] | None = None,
    num_questions: int = 5,
) -> dict:
    """
    Generate a quiz from a video's transcript.

    Args:
        video_id: YouTube video ID
        difficulty: easy, medium, or hard
        question_types: List of types — mcq, short_answer, flashcard
        num_questions: Number of questions per type (1-10)

    Returns:
        Dict with mcqs, short_answers, flashcards lists
    """
    if question_types is None:
        question_types = ["mcq", "short_answer", "flashcard"]

    # Normalize difficulty
    difficulty = difficulty.lower().strip()
    if difficulty not in DIFFICULTY_GUIDELINES:
        difficulty = "medium"

    # Get transcript context
    context = _get_full_transcript_context(video_id)
    if not context:
        return {
            "mcqs": [],
            "short_answers": [],
            "flashcards": [],
            "total_questions": 0,
        }

    # Build type-specific instructions
    type_parts = []
    if "mcq" in question_types:
        type_parts.append(f"- Generate exactly {num_questions} Multiple Choice Questions (MCQs), each with exactly 4 options.")
    if "short_answer" in question_types:
        type_parts.append(f"- Generate exactly {num_questions} Short Answer questions with model answers and 2-3 key points each.")
    if "flashcard" in question_types:
        type_parts.append(f"- Generate exactly {num_questions} Flashcards with a clear front (question/term) and back (answer/definition).")

    type_instructions = "\n".join(type_parts) if type_parts else "- Generate 5 MCQs."

    # Build the prompt
    prompt = QUIZ_PROMPT.format(
        difficulty_guidelines=DIFFICULTY_GUIDELINES[difficulty],
        context=context,
        type_instructions=type_instructions,
        difficulty=difficulty,
    )

    # Call LLM
    print(f"[QuizGen] Generating {difficulty} quiz for video {video_id}...")
    print(f"[QuizGen] Types: {question_types}, Count per type: {num_questions}")

    llm = _get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    raw_text = response.content.strip()

    print(f"[QuizGen] LLM response length: {len(raw_text)} chars")

    # Parse JSON from response
    quiz_data = _parse_quiz_json(raw_text)

    # Validate and trim to requested counts
    result = {
        "mcqs": [],
        "short_answers": [],
        "flashcards": [],
    }

    if "mcq" in question_types:
        mcqs = quiz_data.get("mcqs", [])
        for q in mcqs[:num_questions]:
            # Validate MCQ structure
            if (
                q.get("question")
                and isinstance(q.get("options"), list)
                and len(q["options"]) == 4
                and isinstance(q.get("correct_answer_index"), int)
                and 0 <= q["correct_answer_index"] <= 3
            ):
                result["mcqs"].append({
                    "question": q["question"],
                    "options": q["options"],
                    "correct_answer_index": q["correct_answer_index"],
                    "explanation": q.get("explanation", ""),
                    "timestamp": q.get("timestamp"),
                    "difficulty": difficulty,
                })

    if "short_answer" in question_types:
        shorts = quiz_data.get("short_answers", [])
        for q in shorts[:num_questions]:
            if q.get("question") and q.get("model_answer"):
                result["short_answers"].append({
                    "question": q["question"],
                    "model_answer": q["model_answer"],
                    "key_points": q.get("key_points", []),
                    "timestamp": q.get("timestamp"),
                    "difficulty": difficulty,
                })

    if "flashcard" in question_types:
        cards = quiz_data.get("flashcards", [])
        for q in cards[:num_questions]:
            if q.get("front") and q.get("back"):
                result["flashcards"].append({
                    "front": q["front"],
                    "back": q["back"],
                    "timestamp": q.get("timestamp"),
                    "difficulty": difficulty,
                })

    total = len(result["mcqs"]) + len(result["short_answers"]) + len(result["flashcards"])
    result["total_questions"] = total

    print(f"[QuizGen] ✓ Generated {total} questions "
          f"({len(result['mcqs'])} MCQ, {len(result['short_answers'])} short, "
          f"{len(result['flashcards'])} flashcards)")

    return result


def _parse_quiz_json(raw_text: str) -> dict:
    """
    Parse JSON from LLM response, handling common formatting issues
    like markdown code fences.
    """
    # Try direct parse first
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    cleaned = raw_text
    if "```" in cleaned:
        # Remove ```json ... ``` or ``` ... ```
        cleaned = re.sub(r'```(?:json)?\s*\n?', '', cleaned)
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in the text
    match = re.search(r'\{[\s\S]*\}', raw_text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    print(f"[QuizGen] ⚠ Failed to parse LLM response as JSON")
    print(f"[QuizGen] Raw response: {raw_text[:500]}...")
    return {"mcqs": [], "short_answers": [], "flashcards": []}
