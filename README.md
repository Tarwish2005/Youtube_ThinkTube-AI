# 🎓 YoutuLearn — AI YouTube Video Assistant

An intelligent AI-powered platform that enables users to ask questions about YouTube videos and receive context-aware, timestamp-referenced answers. Built with LangChain, FastAPI, and ChromaDB for efficient video understanding and Q&A.

---

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Architecture & Workflow](#-architecture--workflow)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Running the Application](#-running-the-application)
- [API Documentation](#-api-documentation)
- [Usage Guide](#-usage-guide)
- [Development](#-development)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

- **YouTube Video Processing**: Automatically extract and process YouTube video transcripts
- **RAG (Retrieval-Augmented Generation)**: Intelligent context retrieval for accurate Q&A
- **Timestamp References**: Get answers with exact video timestamps for easy navigation
- **Quiz Generation**: Generate MCQs, short-answer questions, and flashcards from video content
- **Multiple Difficulty Levels**: Easy, Medium, and Hard quiz options
- **Streaming Responses**: Real-time answer streaming for better UX
- **Video Metadata**: Retrieve video details (title, duration, channel, etc.)
- **ChromaDB Vector Storage**: Efficient semantic search across video content
- **CORS Enabled**: Ready for cross-origin frontend requests
- **Stream Processing Support**: Handle audio fallback with Whisper when transcripts unavailable

---

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Python web framework)
- **Runtime**: Uvicorn (ASGI server)
- **LLM Provider**: Groq API (fast inference)
- **AI/RAG**: LangChain + LangGraph (orchestration and memory)
- **Vector Database**: ChromaDB (semantic search)
- **Embeddings**: Sentence Transformers
- **Video Processing**:
  - `youtube-transcript-api`: Extract transcripts
  - `yt-dlp`: Video metadata & fallback downloading
  - `groq-whisper`: Audio transcription fallback
- **Data Validation**: Pydantic + Pydantic Settings
- **Environment**: python-dotenv

### Frontend
- **HTML5**: Semantic markup
- **CSS3**: Responsive styling with modern design
- **Vanilla JavaScript**: Interactive UI without frameworks
- **API Communication**: Fetch API for REST calls

---

## 🏗️ Architecture & Workflow

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Frontend                            │
│                   (HTML/CSS/JS UI)                           │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         /api/process    /api/chat    /api/quiz       │   │
│  │         (Routes Handler)                             │   │
│  └─────────────┬────────────────┬──────────────┬────────┘   │
│                │                │              │             │
│  ┌─────────────▼────┐  ┌────────▼─────┐  ┌────▼──────────┐ │
│  │   Transcript     │  │  RAG Agent   │  │ Quiz Generator│ │
│  │   + Chunker      │  │  (LangChain) │  │  (Groq LLM)   │ │
│  └────────┬─────────┘  └────┬────┬────┘  └────┬──────────┘ │
│           │                 │    │            │             │
│  ┌────────▼─────────────────▼────▼────────────▼──────────┐  │
│  │        VectorStore Service (ChromaDB)                  │  │
│  │  • Embed Text (Sentence Transformers)                  │  │
│  │  • Semantic Search                                     │  │
│  │  • Vector Persistence                                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  External APIs              │
         │  • YouTube (Transcripts)    │
         │  • Groq (LLM)               │
         │  • Sentence Transformers    │
         └─────────────────────────────┘
```

### Workflow: Video Processing to Q&A

#### **Phase 1: Video Processing**
1. User provides YouTube URL
2. Extract video ID and fetch metadata (title, duration, channel)
3. Retrieve transcript using YouTube Transcript API
4. Split transcript into semantic chunks (handled by chunker)
5. Generate embeddings for each chunk using Sentence Transformers
6. Store embeddings in ChromaDB with metadata (video_id, chunk_index, text, timestamp)
7. Return processing status with video metadata

#### **Phase 2: User Query Processing**
1. User enters a question
2. Encode question using same embedding model
3. Search ChromaDB for top-k semantic matches
4. Retrieve relevant chunks with timestamps
5. Build RAG prompt with context + question
6. Send to Groq LLM agent via LangChain
7. Stream response back to frontend
8. Response includes timestamp references for easy navigation

#### **Phase 3: Quiz Generation**
1. User requests quiz for a video
2. Verify video is indexed in ChromaDB
3. Retrieve all chunks for that video
4. Generate quiz questions using Groq LLM
5. Create:
   - Multiple Choice Questions (MCQs)
   - Short Answer Questions
   - Flashcards
6. Return structured quiz data

---

## 📁 Project Structure

```
Youtube_ThinkTube-AI/
│
├── Backend/
│   ├── requirements.txt              # Python dependencies
│   ├── run.py                        # Entry point to start server
│   ├── .env.example                  # Environment variables template
│   │
│   └── App/
│       ├── __init__.py
│       ├── Main.py                   # FastAPI app factory & initialization
│       │
│       ├── Config/
│       │   ├── __init__.py
│       │   └── settings.py           # Environment configuration (Pydantic)
│       │
│       ├── Models/
│       │   ├── __init__.py
│       │   └── schemas.py            # Request/Response Pydantic models
│       │
│       ├── Routes/
│       │   ├── __init__.py
│       │   ├── chat.py               # /api/process, /api/chat endpoints
│       │   └── quiz.py               # /api/quiz/generate endpoint
│       │
│       ├── Services/
│       │   ├── __init__.py
│       │   ├── transcript.py         # YouTube transcript extraction
│       │   ├── chunker.py            # Text chunking & segmentation
│       │   ├── vectorstore.py        # ChromaDB embedding & search
│       │   ├── agent.py              # LangChain RAG agent & LLM integration
│       │   ├── quiz_generator.py     # Quiz question generation logic
│       │   └── whisper_fallback.py   # Audio transcription fallback
│       │
│       └── data/
│           ├── audio_temp/           # Temporary audio files (git-ignored)
│           └── chroma_db/            # ChromaDB vector database (git-ignored)
│
├── Frontend/
│   ├── index.html                    # Main UI page
│   ├── index.css                     # Responsive styling
│   └── app.js                        # JavaScript interactivity & API calls
│
├── .gitignore                        # Git ignore rules
└── README.md                         # This file

```

---

## 📦 Prerequisites

- **Python 3.9+** (tested on 3.10, 3.11)
- **pip** (Python package manager)
- **Groq API Key** (free tier available at [console.groq.com](https://console.groq.com))
- **Node.js/npm** (optional, for frontend development)
- **Git** (for version control)

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Tarwish2005/Youtube_ThinkTube-AI.git
cd Youtube_ThinkTube-AI
```

### 2. Set Up Python Virtual Environment

```bash
# Navigate to backend directory
cd Backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy template to .env
cp .env.example .env

# Edit .env with your configuration
# See Configuration section below
```

---

## ⚙️ Configuration

### Environment Variables (.env)

Create a `.env` file in the `Backend/` directory with the following variables:

```env
# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here

# LLM Model Selection
# Options: mixtral-8x7b-32768, llama2-70b-4096, gemma-7b-it, etc.
LLM_MODEL=mixtral-8x7b-32768

# Vector Store Configuration
VECTOR_DB_PATH=./data/chroma_db
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# CORS Configuration (for frontend dev)
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# Chunking Configuration
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

### Getting Groq API Key

1. Visit [console.groq.com](https://console.groq.com)
2. Sign up or log in
3. Navigate to API Keys section
4. Create new API key
5. Copy and paste into your `.env` file

---

## ▶️ Running the Application

### Start Backend Server

```bash
# From Backend/ directory with venv activated
python run.py
```

**Server will start at:** `http://localhost:8000`

**OpenAPI Docs:** `http://localhost:8000/docs` (interactive Swagger UI)

**ReDoc Docs:** `http://localhost:8000/redoc` (alternative API documentation)

### Access Frontend

Backend serves frontend automatically at root:
- Open browser: `http://localhost:8000`

---

## 📡 API Documentation

### Base URL
```
http://localhost:8000/api
```

### Authentication
No authentication required (currently open API)

---

### **1. Process Video**

**Endpoint:** `POST /api/process`

**Description:** Extract transcript, chunk, embed, and index a YouTube video.

**Request:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "chunk_size": 1000,
  "chunk_overlap": 200
}
```

**Response (200):**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "title": "Video Title",
  "duration": "3:33",
  "channel": "Channel Name",
  "transcript_chunks": 5,
  "indexed": true,
  "processing_time_seconds": 12.5
}
```

**Error Responses:**
- `400`: Invalid YouTube URL
- `500`: Processing failed (transcript unavailable, API error)

---

### **2. Chat (Ask Question)**

**Endpoint:** `POST /api/chat`

**Description:** Ask a question about a processed video (streaming response).

**Request:**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "question": "What is the main topic of this video?"
}
```

**Response (200 - Streaming):**
```
Chained Response Chunks:
"The main topic...[streaming continues]"

Contains metadata:
- timestamps: [{"text": "0:15", "timestamp": 15}]
- confidence: 0.92
- source_chunks: 2
```

**Error Responses:**
- `400`: Video not indexed
- `404`: Invalid video_id
- `500`: LLM error, retrieval failed

---

### **3. Generate Quiz**

**Endpoint:** `POST /api/quiz/generate`

**Description:** Generate MCQs, short answers, and flashcards from video content.

**Request:**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "num_questions": 5,
  "difficulty": "medium"
}
```

**Response (200):**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "difficulty": "medium",
  "quiz": {
    "mcq_questions": [
      {
        "id": 1,
        "question": "Question text?",
        "options": ["A", "B", "C", "D"],
        "answer": "A"
      }
    ],
    "short_answer_questions": [
      {
        "id": 1,
        "question": "Explain...?"
      }
    ],
    "flashcards": [
      {
        "id": 1,
        "front": "Term",
        "back": "Definition"
      }
    ]
  },
  "generated_at": "2024-04-18T10:30:00Z"
}
```

**Error Responses:**
- `400`: Video not indexed, invalid difficulty
- `404`: Invalid video_id
- `500`: Quiz generation failed

---

### **4. Check Video Status**

**Endpoint:** `GET /api/video/{video_id}/status`

**Description:** Check if a video is indexed and get its metadata.

**Response (200):**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "indexed": true,
  "title": "Video Title",
  "chunk_count": 5,
  "last_processed": "2024-04-18T10:15:00Z"
}
```

---

## 💻 Usage Guide

### Step 1: Process a Video
1. Navigate to `http://localhost:8000`
2. Paste a YouTube URL
3. Click "Process Video"
4. Wait for transcript extraction, chunking, and embedding
5. Status bar shows progress

### Step 2: Ask Questions
1. Once video is processed, ask a question in the chat input
2. Type your question (e.g., "What is the main topic?")
3. Click "Send" or press Enter
4. Receive streaming response with timestamps
5. Click timestamp to jump to relevant section in video

### Step 3: Generate Quiz
1. Click "Generate Quiz" button
2. Select difficulty level (Easy/Medium/Hard)
3. Receive MCQs, short answers, and flashcards
4. Review and study

---

## 🔧 Development

### Project Structure Overview

**Backend Services:**
- `transcript.py`: Handles YouTube interaction and text extraction
- `chunker.py`: Semantic text chunking for RAG
- `vectorstore.py`: ChromaDB operations and embeddings
- `agent.py`: LangChain RAG agent orchestration
- `quiz_generator.py`: LLM-based quiz question generation
- `whisper_fallback.py`: Audio transcription when transcripts unavailable

**Frontend Components:**
- `index.html`: UI structure
- `index.css`: Styling and responsive layout
- `app.js`: API integration and interactivity

### Adding New Features

**Example: Add new chat endpoint**
1. Define schema in `Models/schemas.py`
2. Create route in `Routes/chat.py`
3. Implement service logic in `Services/`
4. Update frontend `app.js` to call new endpoint

### Testing

**Manual Testing:**
```bash
# Use OpenAPI docs
http://localhost:8000/docs

# Or use curl
curl -X POST "http://localhost:8000/api/process" \
  -H "Content-Type: application/json" \
  -d '{"youtube_url":"https://www.youtube.com/watch?v=..."}'
```

**Code Style:**
- Python: Follow PEP 8 guidelines
- JavaScript: Use ES6+ syntax
- Docstrings: Include for all functions and classes

---

## 🐛 Troubleshooting

### Issue: "Groq API Key not found"
**Solution:** 
- Verify `.env` file in `Backend/` directory
- Check `GROQ_API_KEY=` is set correctly
- Restart server after updating `.env`

### Issue: "YouTube transcript not available"
**Solution:**
- Verify video has captions (auto-generated captions work)
- Video must have transcripts available
- System will attempt Whisper fallback (requires `yt-dlp`)

### Issue: "ChromaDB connection failed"
**Solution:**
- Verify `data/chroma_db/` directory exists
- Check file permissions
- Delete `chroma.sqlite3` and restart (will recreate)

### Issue: "LLM response is slow"
**Solution:**
- Check internet connection to Groq API
- Monitor Groq API status at [status.groq.com](https://status.groq.com)
- Consider using faster model (e.g., `gemma-7b-it`)

### Issue: "CORS errors in frontend"
**Solution:**
- Verify `CORS_ORIGINS` in `.env` includes frontend URL
- Check browser console for exact error
- Restart server after CORS configuration changes

### Issue: "Server won't start"
**Solution:**
```bash
# Verify port not in use
netstat -an | grep 8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process using port and restart
# Or change PORT in run.py
```

---

## 📝 Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | ✅ Yes | - | Your Groq API key |
| `LLM_MODEL` | ❌ No | `mixtral-8x7b-32768` | LLM model to use |
| `VECTOR_DB_PATH` | ❌ No | `./data/chroma_db` | ChromaDB storage path |
| `EMBEDDING_MODEL` | ❌ No | `all-MiniLM-L6-v2` | Embedding model |
| `SERVER_HOST` | ❌ No | `0.0.0.0` | Server bind address |
| `SERVER_PORT` | ❌ No | `8000` | Server port |
| `CORS_ORIGINS` | ❌ No | `["*"]` | CORS allowed origins |
| `CHUNK_SIZE` | ❌ No | `1000` | Transcript chunk size |
| `CHUNK_OVERLAP` | ❌ No | `200` | Chunk overlap tokens |

---

## 📜 License

This project is open source and available under the MIT License.

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📧 Support

For issues, questions, or suggestions:
1. Check [Troubleshooting](#-troubleshooting) section
2. Review [API Documentation](#-api-documentation)
3. Open an issue on GitHub

---

## 🎯 Roadmap

- [ ] User authentication and sessions
- [ ] Video history and favorites
- [ ] Multi-language support
- [ ] Advanced search filters
- [ ] Custom LLM model selection UI
- [ ] Batch video processing
- [ ] Export quiz to PDF/Excel
- [ ] Real-time collaboration

---

**Last Updated:** April 18, 2026  
**Version:** 1.0.0  
**Status:** Production Ready
