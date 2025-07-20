"""
Vector Database and RAG Integration for Jarvis Multi-Agent AI System.

This module provides Qdrant integration for vector storage, embedding generation,
semantic search, and RAG (Retrieval-Augmented Generation) functionality.
"""

import asyncio
import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

import numpy as np
from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, 
    MatchValue, Range, SearchRequest, UpdateResult
)
from sentence_transformers import SentenceTransformer
import structlog

from models.database import FileIndex, DocumentChunk, FileIndexCreate, DocumentChunkCreate

logger = structlog.get_logger(__name__)

class EmbeddingError(Exception):
    """Exception for embedding generation errors."""
    pass

class VectorSearchError(Exception):
    """Exception for vector search errors."""
    pass

class DocumentProcessor:
    """Document processing and chunking utilities."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks."""
        if not text.strip():
            return []
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + self.chunk_size // 2:
                    end = sentence_end + 1
                else:
                    # Look for word boundaries
                    word_end = text.rfind(' ', start, end)
                    if word_end > start + self.chunk_size // 2:
                        end = word_end
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk_metadata = metadata.copy() if metadata else {}
                chunk_metadata.update({
                    "chunk_index": chunk_index,
                    "start_char": start,
                    "end_char": end,
                    "chunk_length": len(chunk_text)
                })
                
                chunks.append({
                    "content": chunk_text,
                    "metadata": chunk_metadata,
                    "chunk_index": chunk_index
                })
                chunk_index += 1
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    def extract_text_from_file(self, file_path: Path) -> str:
        """Extract text from various file formats."""
        try:
            suffix = file_path.suffix.lower()
            
            if suffix == '.txt':
                return file_path.read_text(encoding='utf-8')
            elif suffix == '.md':
                return file_path.read_text(encoding='utf-8')
            elif suffix == '.json':
                import json
                data = json.loads(file_path.read_text(encoding='utf-8'))
                return json.dumps(data, indent=2)
            elif suffix == '.csv':
                import pandas as pd
                df = pd.read_csv(file_path)
                return df.to_string()
            elif suffix == '.pdf':
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as file:
                        reader = PyPDF2.PdfReader(file)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() + "\n"
                        return text
                except ImportError:
                    logger.warning("PyPDF2 not installed, cannot process PDF files")
                    return ""
            elif suffix == '.docx':
                try:
                    import docx
                    doc = docx.Document(file_path)
                    text = ""
                    for paragraph in doc.paragraphs:
                        text += paragraph.text + "\n"
                    return text
                except ImportError:
                    logger.warning("python-docx not installed, cannot process DOCX files")
                    return ""
            else:
                logger.warning(f"Unsupported file format: {suffix}")
                return ""
                
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            return ""

class EmbeddingGenerator:
    """Generate embeddings using various models."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self.model = None
        self.embedding_dim = None
    
    async def _load_model(self):
        """Load the embedding model."""
        if self.model is None:
            try:
                self.model = SentenceTransformer(self.model_name, device=self.device)
                # Get embedding dimension
                test_embedding = self.model.encode(["test"])
                self.embedding_dim = len(test_embedding[0])
                logger.info(f"Loaded embedding model: {self.model_name}, dim: {self.embedding_dim}")
            except Exception as e:
                raise EmbeddingError(f"Failed to load embedding model: {e}")
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []
        
        await self._load_model()
        
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embeddings: {e}")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embeddings = await self.generate_embeddings([text])
        return embeddings[0] if embeddings else []

class QdrantVectorStore:
    """Qdrant vector database integration."""
    
    def __init__(self, url: str = "http://localhost:6333", collection_name: str = "jarvis_documents"):
        self.url = url
        self.collection_name = collection_name
        self.client = None
        self.embedding_generator = EmbeddingGenerator()
    
    async def _get_client(self) -> AsyncQdrantClient:
        """Get or create Qdrant client."""
        if self.client is None:
            self.client = AsyncQdrantClient(url=self.url)
        return self.client
    
    async def initialize_collection(self, embedding_dim: int = 384):
        """Initialize Qdrant collection if it doesn't exist."""
        client = await self._get_client()
        
        try:
            # Check if collection exists
            collections = await client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                await client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Qdrant collection already exists: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant collection: {e}")
            raise
    
    async def add_documents(self, documents: List[Dict[str, Any]], file_id: UUID) -> List[str]:
        """Add documents to the vector store."""
        if not documents:
            return []
        
        client = await self._get_client()
        
        try:
            # Generate embeddings
            texts = [doc["content"] for doc in documents]
            embeddings = await self.embedding_generator.generate_embeddings(texts)
            
            # Ensure collection exists
            await self.initialize_collection(len(embeddings[0]) if embeddings else 384)
            
            # Create points
            points = []
            point_ids = []
            
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                point_id = str(uuid4())
                point_ids.append(point_id)
                
                payload = {
                    "file_id": str(file_id),
                    "chunk_index": doc["chunk_index"],
                    "content": doc["content"],
                    "metadata": doc["metadata"]
                }
                
                points.append(PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                ))
            
            # Upsert points
            await client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Added {len(points)} document chunks to Qdrant")
            return point_ids
            
        except Exception as e:
            logger.error(f"Failed to add documents to Qdrant: {e}")
            raise VectorSearchError(f"Failed to add documents: {e}")
    
    async def search_similar(
        self, 
        query: str, 
        limit: int = 10, 
        score_threshold: float = 0.7,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        client = await self._get_client()
        
        try:
            # Generate query embedding
            query_embedding = await self.embedding_generator.generate_embedding(query)
            
            # Build filter
            query_filter = None
            if filter_conditions:
                must_conditions = []
                for key, value in filter_conditions.items():
                    if isinstance(value, str):
                        must_conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
                    elif isinstance(value, (int, float)):
                        must_conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
                    elif isinstance(value, dict) and "gte" in value:
                        must_conditions.append(FieldCondition(key=key, range=Range(gte=value["gte"])))
                
                if must_conditions:
                    query_filter = Filter(must=must_conditions)
            
            # Search
            search_result = await client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Format results
            results = []
            for hit in search_result:
                results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "content": hit.payload.get("content", ""),
                    "metadata": hit.payload.get("metadata", {}),
                    "file_id": hit.payload.get("file_id"),
                    "chunk_index": hit.payload.get("chunk_index")
                })
            
            logger.info(f"Found {len(results)} similar documents for query")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search similar documents: {e}")
            raise VectorSearchError(f"Search failed: {e}")
    
    async def delete_documents(self, file_id: UUID) -> bool:
        """Delete all documents for a specific file."""
        client = await self._get_client()
        
        try:
            # Delete points with matching file_id
            await client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key="file_id", match=MatchValue(value=str(file_id)))]
                )
            )
            
            logger.info(f"Deleted documents for file_id: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return False
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        client = await self._get_client()
        
        try:
            info = await client.get_collection(self.collection_name)
            return {
                "name": info.config.name,
                "status": info.status,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "config": {
                    "vector_size": info.config.params.vectors.size,
                    "distance": info.config.params.vectors.distance.name
                }
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {}

class RAGSystem:
    """Retrieval-Augmented Generation system."""
    
    def __init__(self, vector_store: QdrantVectorStore, document_processor: DocumentProcessor):
        self.vector_store = vector_store
        self.document_processor = document_processor
    
    async def ingest_file(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> UUID:
        """Ingest a file into the RAG system."""
        try:
            # Extract text
            text = self.document_processor.extract_text_from_file(file_path)
            if not text.strip():
                raise ValueError(f"No text extracted from file: {file_path}")
            
            # Generate file hash
            file_hash = hashlib.sha256(text.encode()).hexdigest()
            
            # Create file index entry
            file_id = uuid4()
            
            # Chunk the text
            chunks = self.document_processor.chunk_text(text, metadata)
            
            # Add to vector store
            await self.vector_store.add_documents(chunks, file_id)
            
            logger.info(f"Ingested file: {file_path}, chunks: {len(chunks)}")
            
            return file_id
            
        except Exception as e:
            logger.error(f"Failed to ingest file {file_path}: {e}")
            raise
    
    async def search_and_retrieve(
        self, 
        query: str, 
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Search for relevant documents and create context."""
        try:
            # Search for similar documents
            results = await self.vector_store.search_similar(
                query=query,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Create context from results
            context_parts = []
            for i, result in enumerate(results, 1):
                context_parts.append(f"[Document {i}] {result['content']}")
            
            context = "\n\n".join(context_parts)
            
            return results, context
            
        except Exception as e:
            logger.error(f"Failed to search and retrieve: {e}")
            raise
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics."""
        try:
            collection_info = await self.vector_store.get_collection_info()
            
            return {
                "collection_info": collection_info,
                "embedding_model": self.vector_store.embedding_generator.model_name,
                "chunk_size": self.document_processor.chunk_size,
                "chunk_overlap": self.document_processor.chunk_overlap
            }
            
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return {}
