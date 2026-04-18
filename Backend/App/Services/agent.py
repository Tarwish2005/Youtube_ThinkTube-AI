"""
LangGraph RAG Agent for YouTube video Q&A.

Simplified, reliable flow:
    Router → Retrieve → Generate (always uses transcript context)
    Router → Direct (only for greetings/meta questions)

The agent maintains conversation memory per thread and returns
answers grounded in video transcript chunks with timestamp references.
"""

import json
import uuid
from typing import Annotated, Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict

from App.Config.settings import get_settings
from App.Services.vectorstore import VectorStoreService
from App.Services.transcript import format_duration


# ═══════════════════════════════════════════════════════════════
# State Definition
# ═══════════════════════════════════════════════════════════════

class AgentState(TypedDict):
    """Shared state across all graph nodes."""
    messages: Annotated[list, add_messages]
    documents: list[dict]
    video_id: str
    query: str
    generation: str


# ═══════════════════════════════════════════════════════════════
# Prompts
# ═══════════════════════════════════════════════════════════════

ROUTER_PROMPT = """You are a query router for a YouTube video Q&A system.
Decide whether the user's message needs to search the video transcript.

Respond with ONLY one word:
- "retrieve" — if the question is about the video, its content, topics, 
  what was said, summaries, explanations, key points, or ANYTHING that 
  could be answered using the video transcript.
- "direct" — ONLY for greetings (hi, hello), thank you messages, or 
  questions about how this chatbot works.

IMPORTANT: When in doubt, ALWAYS choose "retrieve". Most questions need the transcript.

User message: {query}"""

RAG_GENERATE_PROMPT = """You are an intelligent YouTube video learning assistant. 
Answer the user's question based on the transcript excerpts provided below.

RULES:
1. Use the transcript context to provide a thorough, helpful answer.
2. Include timestamps in [MM:SS] format when referring to specific parts.
3. If the transcript is in a non-English language, still answer in the 
   language the user asked their question in.
4. Synthesize information from multiple sections when needed.
5. Be educational, clear, and engaging.
6. If the context seems limited, provide the best answer you can from 
   what's available and mention that the answer is based on available excerpts.

Video Transcript Context:
{context}

Previous Conversation:
{chat_history}

User Question: {query}

Answer:"""

DIRECT_RESPONSE_PROMPT = """You are a friendly YouTube video learning assistant 
called YoutuLearn. The user sent a casual message that doesn't need the video 
transcript. Respond warmly.

If they're greeting you, welcome them and suggest they can ask questions like:
- "What is this video about?"
- "Summarize the key points"  
- "Explain [topic] from the video"

User message: {query}"""


# ═══════════════════════════════════════════════════════════════
# LLM
# ═══════════════════════════════════════════════════════════════

def _get_llm():
    settings = get_settings()
    return ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.3,
        max_tokens=2048,
    )


# ═══════════════════════════════════════════════════════════════
# Node Functions
# ═══════════════════════════════════════════════════════════════

def route_decision(state: AgentState) -> Literal["retrieve", "direct"]:
    """Classify: does this query need the transcript?"""
    query = state["query"].strip().lower()

    # Fast path: obvious greetings don't need LLM
    greetings = ["hi", "hello", "hey", "thanks", "thank you", "bye", "help"]
    if query in greetings or len(query) < 4:
        return "direct"

    # For everything else, ask the LLM
    try:
        llm = _get_llm()
        response = llm.invoke([HumanMessage(
            content=ROUTER_PROMPT.format(query=state["query"])
        )])
        decision = response.content.strip().lower()
        if "direct" in decision:
            print(f"[Agent] Router → direct (query: {state['query'][:50]})")
            return "direct"
    except Exception as e:
        print(f"[Agent] Router error, defaulting to retrieve: {e}")

    print(f"[Agent] Router → retrieve (query: {state['query'][:50]})")
    return "retrieve"


def retrieve_node(state: AgentState) -> dict:
    """Retrieve relevant transcript chunks from the vector store."""
    video_id = state["video_id"]
    query = state["query"]

    vectorstore = VectorStoreService()
    documents = vectorstore.search(video_id=video_id, query=query, k=5)

    print(f"[Agent] Retrieved {len(documents)} chunks for query: '{query[:60]}'")
    for i, doc in enumerate(documents):
        start = format_duration(doc["start_time"])
        print(f"  [{start}] score={doc.get('score', 0):.3f} | {doc['text'][:80]}...")

    return {"documents": documents}


def generate_node(state: AgentState) -> dict:
    """Generate the final answer using retrieved context + conversation history."""
    llm = _get_llm()
    query = state["query"]
    documents = state.get("documents", [])
    messages = state.get("messages", [])

    # Build context with timestamps
    context_parts = []
    for doc in documents:
        start_fmt = format_duration(doc["start_time"])
        end_fmt = format_duration(doc["end_time"])
        context_parts.append(f"[{start_fmt} - {end_fmt}]: {doc['text']}")

    context = "\n\n".join(context_parts) if context_parts else (
        "No specific transcript sections were retrieved. "
        "Please try asking a more specific question about the video."
    )

    # Build chat history (last 6 messages)
    chat_lines = []
    recent = messages[-6:] if len(messages) > 6 else messages
    for msg in recent:
        if isinstance(msg, HumanMessage):
            chat_lines.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            chat_lines.append(f"Assistant: {msg.content[:200]}...")
    chat_history = "\n".join(chat_lines) or "No previous conversation."

    # Generate answer
    response = llm.invoke([HumanMessage(
        content=RAG_GENERATE_PROMPT.format(
            context=context,
            chat_history=chat_history,
            query=query,
        )
    )])

    answer = response.content
    print(f"[Agent] Generated answer ({len(answer)} chars)")

    return {
        "generation": answer,
        "messages": [AIMessage(content=answer)],
    }


def direct_response_node(state: AgentState) -> dict:
    """Handle greetings and meta questions without transcript search."""
    llm = _get_llm()
    response = llm.invoke([HumanMessage(
        content=DIRECT_RESPONSE_PROMPT.format(query=state["query"])
    )])
    answer = response.content
    return {
        "generation": answer,
        "documents": [],
        "messages": [AIMessage(content=answer)],
    }


# Dummy entry node (needed because conditional edges run before the node)
def entry_node(state: AgentState) -> dict:
    """Entry point — just passes through."""
    return {}


# ═══════════════════════════════════════════════════════════════
# Graph Construction
# ═══════════════════════════════════════════════════════════════

def build_rag_graph():
    """
    Build the RAG agent graph.

    Simplified flow:
        entry → [route] → retrieve → generate → END
                        → direct → END
    """
    graph = StateGraph(AgentState)

    graph.add_node("entry", entry_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("direct", direct_response_node)

    graph.set_entry_point("entry")

    graph.add_conditional_edges(
        "entry",
        route_decision,
        {"retrieve": "retrieve", "direct": "direct"},
    )

    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    graph.add_edge("direct", END)

    memory = MemorySaver()
    compiled = graph.compile(checkpointer=memory)
    return compiled


# ═══════════════════════════════════════════════════════════════
# Agent Interface
# ═══════════════════════════════════════════════════════════════

_graph = None

def get_graph():
    global _graph
    if _graph is None:
        print("[Agent] Building LangGraph RAG agent...")
        _graph = build_rag_graph()
        print("[Agent] ✓ RAG agent ready.")
    return _graph


async def chat(message: str, video_id: str, thread_id: str | None = None) -> dict:
    """Send a message and get a complete response."""
    if not thread_id:
        thread_id = str(uuid.uuid4())

    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    result = graph.invoke(
        {
            "messages": [HumanMessage(content=message)],
            "query": message,
            "video_id": video_id,
            "documents": [],
            "generation": "",
        },
        config=config,
    )

    answer = result.get("generation", "I couldn't generate an answer.")
    documents = result.get("documents", [])

    timestamps = [
        {
            "text": doc["text"][:150] + "..." if len(doc["text"]) > 150 else doc["text"],
            "start_time": doc["start_time"],
            "end_time": doc["end_time"],
            "url": doc.get("url", f"https://www.youtube.com/watch?v={video_id}&t={int(doc['start_time'])}s"),
        }
        for doc in documents
    ]

    return {"answer": answer, "timestamps": timestamps, "thread_id": thread_id}


def stream_chat(message: str, video_id: str, thread_id: str | None = None):
    """Stream responses as a sync generator for SSE."""
    if not thread_id:
        thread_id = str(uuid.uuid4())

    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    input_state = {
        "messages": [HumanMessage(content=message)],
        "query": message,
        "video_id": video_id,
        "documents": [],
        "generation": "",
    }

    final_answer = ""
    final_documents = []

    for event in graph.stream(input_state, config=config, stream_mode="updates"):
        for node_name, node_output in event.items():
            if node_output is None:
                continue

            yield json.dumps({
                "type": "status",
                "node": node_name,
                "message": f"Processing: {node_name}",
            })

            if node_name in ("generate", "direct"):
                gen = node_output.get("generation")
                if gen:
                    final_answer = gen

            docs = node_output.get("documents")
            if docs:
                final_documents = docs

    timestamps = []
    for doc in final_documents:
        if doc is None:
            continue
        timestamps.append({
            "text": (doc["text"][:150] + "...") if len(doc.get("text", "")) > 150 else doc.get("text", ""),
            "start_time": doc.get("start_time", 0),
            "end_time": doc.get("end_time", 0),
            "url": doc.get("url", f"https://www.youtube.com/watch?v={video_id}&t={int(doc.get('start_time', 0))}s"),
        })

    yield json.dumps({
        "type": "answer",
        "content": final_answer,
        "timestamps": timestamps,
        "thread_id": thread_id,
    })

    yield json.dumps({"type": "done"})

