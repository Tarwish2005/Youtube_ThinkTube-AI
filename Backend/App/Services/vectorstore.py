"""
Vector store service using ChromaDB + sentence-transformers.
Handles embedding, indexing, and similarity search for transcript chunks.
"""

import chromadb
from sentence_transformers import SentenceTransformer
from App.Services.chunker import TranscriptChunk
from App.Config.settings import get_settings


class VectorStoreService:
    """Manages ChromaDB collections for video transcript embeddings."""

    _instance = None
    _initialized = False

    def __new__(cls):
        """Singleton pattern — only one vector store instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if VectorStoreService._initialized:
            return

        settings = get_settings()

        # Initialize embedding model
        print(f"[VectorStore] Loading embedding model: {settings.EMBEDDING_MODEL}...")
        self.embed_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        print("[VectorStore] Embedding model loaded.")

        # Initialize ChromaDB persistent client
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)

        VectorStoreService._initialized = True

    def _get_collection_name(self, video_id: str) -> str:
        """Generate a valid ChromaDB collection name for a video."""
        # ChromaDB collection names: 3-63 chars, alphanumeric + underscores/hyphens
        name = f"vid_{video_id}"
        return name[:63]

    def is_video_indexed(self, video_id: str) -> bool:
        """Check if a video has already been indexed."""
        collection_name = self._get_collection_name(video_id)
        try:
            collection = self.client.get_collection(name=collection_name)
            return collection.count() > 0
        except Exception:
            return False

    def get_chunk_count(self, video_id: str) -> int:
        """Get the number of indexed chunks for a video."""
        collection_name = self._get_collection_name(video_id)
        try:
            collection = self.client.get_collection(name=collection_name)
            return collection.count()
        except Exception:
            return 0

    def index_video(self, video_id: str, chunks: list[TranscriptChunk]) -> int:
        """
        Embed and store transcript chunks in ChromaDB.

        Args:
            video_id: YouTube video ID
            chunks: List of TranscriptChunk objects

        Returns:
            Number of chunks indexed
        """
        if not chunks:
            return 0

        collection_name = self._get_collection_name(video_id)

        # Delete existing collection if re-indexing
        try:
            self.client.delete_collection(name=collection_name)
        except Exception:
            pass

        collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Prepare data for batch insertion
        texts = [chunk.text for chunk in chunks]
        ids = [f"{video_id}_chunk_{chunk.chunk_index}" for chunk in chunks]
        metadatas = [
            {
                "video_id": chunk.video_id,
                "start_time": chunk.start_time,
                "end_time": chunk.end_time,
                "chunk_index": chunk.chunk_index,
            }
            for chunk in chunks
        ]

        # Generate embeddings
        embeddings = self.embed_model.encode(texts, show_progress_bar=False).tolist()

        # Batch insert into ChromaDB
        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        print(f"[VectorStore] Indexed {len(chunks)} chunks for video {video_id}")
        return len(chunks)

    def search(
        self,
        video_id: str,
        query: str,
        k: int = 5,
    ) -> list[dict]:
        """
        Search for relevant transcript chunks.

        Args:
            video_id: YouTube video ID to search within
            query: User's search query
            k: Number of results to return

        Returns:
            List of dicts with 'text', 'start_time', 'end_time', 'score'
        """
        collection_name = self._get_collection_name(video_id)

        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception:
            return []

        # Embed the query
        query_embedding = self.embed_model.encode([query]).tolist()

        # Search
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=min(k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        formatted = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i]
                distance = results["distances"][0][i]

                formatted.append({
                    "text": doc,
                    "start_time": meta["start_time"],
                    "end_time": meta["end_time"],
                    "chunk_index": meta["chunk_index"],
                    "score": 1 - distance,  # Convert distance to similarity
                    "url": f"https://www.youtube.com/watch?v={video_id}&t={int(meta['start_time'])}s",
                })

        # Sort by relevance score (highest first)
        formatted.sort(key=lambda x: x["score"], reverse=True)
        return formatted

    def delete_video(self, video_id: str) -> bool:
        """Delete all indexed data for a video."""
        collection_name = self._get_collection_name(video_id)
        try:
            self.client.delete_collection(name=collection_name)
            print(f"[VectorStore] Deleted collection for video {video_id}")
            return True
        except Exception:
            return False
