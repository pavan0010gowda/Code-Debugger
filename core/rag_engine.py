import os
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter
from core.config import KNOWLEDGE_BASE_DIR, CHROMA_PERSIST_DIR


class CodeReviewRAGEngine:
    """
    Vector database & Agentic RAG engine using ChromaDB.
    Indexes clean code standards, PEP 8 rules, security patterns (CWE/OWASP),
    and runtime bug traps to ground agents in authoritative standards.
    """

    COLLECTION_NAME = "code_review_standards"

    def __init__(self, persist_directory: Optional[Path] = None):
        self.persist_dir = str(persist_directory or CHROMA_PERSIST_DIR)
        
        # Initialize persistent ChromaDB client
        self.chroma_client = chromadb.PersistentClient(path=self.persist_dir)
        
        # Use Chroma's robust default embedding function (all-MiniLM-L6-v2 ONNX)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Auto-index knowledge base if collection is empty
        if self.collection.count() == 0:
            self.index_knowledge_base()

    def index_knowledge_base(self) -> int:
        """Read all markdown documents from knowledge_base directory and index them."""
        doc_files = glob.glob(str(KNOWLEDGE_BASE_DIR / "*.md"))
        if not doc_files:
            return 0

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=80,
            separators=["\n## ", "\n### ", "\n\n", "\n", " "]
        )

        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        ids: List[str] = []

        chunk_counter = 0
        for file_path in doc_files:
            filename = Path(file_path).name
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            chunks = splitter.split_text(content)
            for i, chunk in enumerate(chunks):
                chunk_id = f"{filename}_chunk_{i}_{chunk_counter}"
                documents.append(chunk)
                metadatas.append({
                    "source": filename,
                    "chunk_index": i,
                    "title": filename.replace(".md", "").replace("_", " ").title()
                })
                ids.append(chunk_id)
                chunk_counter += 1

        if documents:
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

        return len(documents)

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Query ChromaDB for the most relevant guideline documents.
        Returns a list of dicts with content, source, and similarity score.
        """
        if not query or self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, self.collection.count())
        )

        retrieved_docs = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
            distances = results["distances"][0] if "distances" in results and results["distances"] else [0.0] * len(docs)

            for doc, meta, dist in zip(docs, metas, distances):
                # Cosine distance to similarity: similarity = 1 - distance
                similarity = round(max(0.0, 1.0 - dist), 3)
                retrieved_docs.append({
                    "content": doc,
                    "source": meta.get("source", "Unknown"),
                    "title": meta.get("title", "Guideline"),
                    "similarity": similarity
                })

        return retrieved_docs

    def format_retrieved_context(self, retrieved_docs: List[Dict[str, Any]]) -> str:
        """Format retrieved documents into a clean context block for LLM prompts."""
        if not retrieved_docs:
            return "No specific external guideline retrieved. Rely on standard language specifications."

        formatted_chunks = []
        for i, doc in enumerate(retrieved_docs, start=1):
            formatted_chunks.append(
                f"[Source {i}: {doc['title']} ({doc['source']}) | Relevance: {doc['similarity']}]\n{doc['content']}"
            )
        return "\n\n---\n\n".join(formatted_chunks)


# Global singleton instance helper
_rag_engine_instance: Optional[CodeReviewRAGEngine] = None

def get_rag_engine() -> CodeReviewRAGEngine:
    """Get or create singleton instance of CodeReviewRAGEngine."""
    global _rag_engine_instance
    if _rag_engine_instance is None:
        _rag_engine_instance = CodeReviewRAGEngine()
    return _rag_engine_instance

