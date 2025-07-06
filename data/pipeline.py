"""
Data pipeline for ingesting and processing Richmond content
Handles document chunking, embedding, and storage with monitoring
"""
import os
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
from pathlib import Path
import numpy as np
import time

from .models import RichmondContent, generate_id
from .repositories import RichmondContentRepository
from .cache import entity_cache
from pinecone import Pinecone, ServerlessSpec
import tiktoken

logger = logging.getLogger('storygen.pipeline')


@dataclass
class PipelineConfig:
    """Configuration for data pipeline"""
    # Chunking settings
    chunk_size: int = 1000
    chunk_overlap: int = 100
    min_chunk_size: int = 100
    
    # Embedding settings
    embedding_model: str = "amazon.titan-embed-text-v1"
    embedding_dimension: int = 1536
    batch_size: int = 25
    
    # Processing settings
    max_workers: int = 4
    process_timeout: int = 300  # 5 minutes
    
    # Pinecone settings
    pinecone_api_key: str = os.environ.get("PINECONE_API_KEY", "")
    pinecone_index_name: str = "richmond-stories"
    pinecone_environment: str = "us-east-1"
    
    # AWS settings
    aws_region: str = "us-east-1"
    bedrock_endpoint: Optional[str] = None
    
    # Data directories
    data_dir: str = "data"
    processed_dir: str = "data/processed"
    failed_dir: str = "data/failed"


class ChunkingStrategy:
    """Smart chunking strategies for different content types"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def chunk_document(self, content: str, content_type: str) -> List[Dict[str, Any]]:
        """Chunk document based on content type"""
        if content_type == "quotes":
            return self._chunk_quotes(content)
        elif content_type == "stories":
            return self._chunk_stories(content)
        elif content_type == "news":
            return self._chunk_news(content)
        else:
            return self._chunk_generic(content)
    
    def _chunk_quotes(self, content: str) -> List[Dict[str, Any]]:
        """Chunk quotes - keep each quote intact"""
        chunks = []
        
        # Split by common quote delimiters
        quote_blocks = content.split("\n\n")
        
        for i, block in enumerate(quote_blocks):
            if block.strip():
                chunks.append({
                    "content": block.strip(),
                    "chunk_index": i,
                    "metadata": {"chunk_type": "quote"}
                })
        
        return chunks
    
    def _chunk_stories(self, content: str) -> List[Dict[str, Any]]:
        """Chunk stories - preserve narrative flow"""
        chunks = []
        
        # Split by paragraphs first
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        
        current_chunk = ""
        chunk_index = 0
        
        for para in paragraphs:
            # Check if adding this paragraph would exceed chunk size
            test_chunk = current_chunk + "\n\n" + para if current_chunk else para
            token_count = len(self.tokenizer.encode(test_chunk))
            
            if token_count > self.config.chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    "content": current_chunk,
                    "chunk_index": chunk_index,
                    "metadata": {"chunk_type": "story_segment"}
                })
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = overlap_text + "\n\n" + para if overlap_text else para
                chunk_index += 1
            else:
                current_chunk = test_chunk
        
        # Add final chunk
        if current_chunk:
            chunks.append({
                "content": current_chunk,
                "chunk_index": chunk_index,
                "metadata": {"chunk_type": "story_segment"}
            })
        
        return chunks
    
    def _chunk_news(self, content: str) -> List[Dict[str, Any]]:
        """Chunk news articles - preserve article boundaries"""
        chunks = []
        
        # Look for article markers (dates, headlines)
        sections = content.split("\n---\n")  # Common article separator
        
        for i, section in enumerate(sections):
            if section.strip():
                # Extract date if present
                lines = section.strip().split("\n")
                metadata = {"chunk_type": "news_article"}
                
                # Simple date detection
                if lines and any(month in lines[0] for month in 
                                ["January", "February", "March", "April", "May", "June",
                                 "July", "August", "September", "October", "November", "December"]):
                    metadata["date"] = lines[0]
                
                chunks.append({
                    "content": section.strip(),
                    "chunk_index": i,
                    "metadata": metadata
                })
        
        # If no clear sections, fall back to generic chunking
        if not chunks:
            return self._chunk_generic(content)
        
        return chunks
    
    def _chunk_generic(self, content: str) -> List[Dict[str, Any]]:
        """Generic chunking with overlap"""
        chunks = []
        
        # Split into sentences for better boundaries
        sentences = content.replace("\n", " ").split(". ")
        sentences = [s.strip() + "." for s in sentences if s.strip()]
        
        current_chunk = ""
        chunk_index = 0
        
        for sentence in sentences:
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            token_count = len(self.tokenizer.encode(test_chunk))
            
            if token_count > self.config.chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    "content": current_chunk,
                    "chunk_index": chunk_index,
                    "metadata": {"chunk_type": "generic"}
                })
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = overlap_text + " " + sentence if overlap_text else sentence
                chunk_index += 1
            else:
                current_chunk = test_chunk
        
        # Add final chunk
        if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
            chunks.append({
                "content": current_chunk,
                "chunk_index": chunk_index,
                "metadata": {"chunk_type": "generic"}
            })
        
        return chunks
    
    def _get_overlap(self, text: str) -> str:
        """Get overlap text for continuity"""
        if not text:
            return ""
        
        # Get last N tokens as overlap
        tokens = self.tokenizer.encode(text)
        if len(tokens) > self.config.chunk_overlap:
            overlap_tokens = tokens[-self.config.chunk_overlap:]
            return self.tokenizer.decode(overlap_tokens)
        
        return text


class EmbeddingGenerator:
    """Generate embeddings using AWS Bedrock"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.bedrock = boto3.client(
            'bedrock-runtime',
            region_name=config.aws_region,
            endpoint_url=config.bedrock_endpoint
        )
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for single text"""
        try:
            response = self.bedrock.invoke_model(
                modelId=self.config.embedding_model,
                body=json.dumps({"inputText": text}),
                contentType="application/json",
                accept="application/json"
            )
            
            result = json.loads(response['body'].read())
            embedding = result.get('embedding')
            
            if embedding and len(embedding) == self.config.embedding_dimension:
                return embedding
            else:
                logger.error(f"Invalid embedding dimension: {len(embedding) if embedding else 0}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts"""
        embeddings = []
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_text = {
                executor.submit(self.generate_embedding, text): i 
                for i, text in enumerate(texts)
            }
            
            # Initialize results list
            results = [None] * len(texts)
            
            for future in as_completed(future_to_text):
                index = future_to_text[future]
                try:
                    embedding = future.result()
                    results[index] = embedding
                except Exception as e:
                    logger.error(f"Failed to generate embedding for index {index}: {e}")
                    results[index] = None
        
        return results


class VectorIndexManager:
    """Manage Pinecone vector index"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.pc = Pinecone(api_key=config.pinecone_api_key)
        self._index = None
    
    @property
    def index(self):
        """Get or create Pinecone index"""
        if self._index is None:
            # Check if index exists
            existing_indexes = self.pc.list_indexes()
            
            if self.config.pinecone_index_name not in [idx.name for idx in existing_indexes]:
                # Create index
                self.pc.create_index(
                    name=self.config.pinecone_index_name,
                    dimension=self.config.embedding_dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.config.pinecone_environment
                    )
                )
                logger.info(f"Created Pinecone index: {self.config.pinecone_index_name}")
            
            self._index = self.pc.Index(self.config.pinecone_index_name)
        
        return self._index
    
    def upsert_vectors(self, vectors: List[Tuple[str, List[float], Dict[str, Any]]]) -> Dict[str, int]:
        """Upsert vectors to index"""
        try:
            # Format for Pinecone
            formatted_vectors = [
                {
                    "id": vector_id,
                    "values": embedding,
                    "metadata": metadata
                }
                for vector_id, embedding, metadata in vectors
            ]
            
            # Upsert in batches
            upserted = 0
            for i in range(0, len(formatted_vectors), self.config.batch_size):
                batch = formatted_vectors[i:i + self.config.batch_size]
                response = self.index.upsert(vectors=batch)
                upserted += response.upserted_count
            
            return {"upserted": upserted, "total": len(vectors)}
            
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            return {"upserted": 0, "total": len(vectors), "error": str(e)}
    
    def delete_vectors(self, vector_ids: List[str]) -> bool:
        """Delete vectors from index"""
        try:
            self.index.delete(ids=vector_ids)
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return False
    
    def query_similar(self, embedding: List[float], top_k: int = 5, 
                     filter: Optional[Dict] = None) -> List[Dict]:
        """Query similar vectors"""
        try:
            results = self.index.query(
                vector=embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter
            )
            
            return [
                {
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata
                }
                for match in results.matches
            ]
            
        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")
            return []


class DataPipeline:
    """Main data processing pipeline"""
    
    def __init__(self, config: PipelineConfig = PipelineConfig()):
        self.config = config
        self.chunker = ChunkingStrategy(config)
        self.embedder = EmbeddingGenerator(config)
        self.vector_manager = VectorIndexManager(config)
        self.content_repo = RichmondContentRepository()
        
        # Create directories
        Path(config.processed_dir).mkdir(parents=True, exist_ok=True)
        Path(config.failed_dir).mkdir(parents=True, exist_ok=True)
        
        # Pipeline statistics
        self.stats = {
            "files_processed": 0,
            "chunks_created": 0,
            "embeddings_generated": 0,
            "vectors_indexed": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    async def process_directory(self, directory: str = None) -> Dict[str, Any]:
        """Process all documents in directory"""
        directory = directory or self.config.data_dir
        self.stats["start_time"] = datetime.utcnow()
        
        logger.info(f"Starting pipeline processing for directory: {directory}")
        
        # Get all markdown files
        data_path = Path(directory)
        md_files = list(data_path.glob("*.md"))
        
        if not md_files:
            logger.warning(f"No markdown files found in {directory}")
            return self._finalize_stats()
        
        # Process files in parallel
        tasks = []
        for file_path in md_files:
            task = asyncio.create_task(self._process_file(file_path))
            tasks.append(task)
        
        # Wait for all tasks with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.process_timeout
            )
        except asyncio.TimeoutError:
            logger.error("Pipeline processing timeout")
            self.stats["errors"] += 1
        
        return self._finalize_stats()
    
    async def _process_file(self, file_path: Path) -> bool:
        """Process single file through pipeline"""
        logger.info(f"Processing file: {file_path.name}")
        
        try:
            # Read file content
            content = file_path.read_text(encoding='utf-8')
            
            # Determine content type from filename
            content_type = self._get_content_type(file_path.name)
            
            # Chunk the document
            chunks = self.chunker.chunk_document(content, content_type)
            logger.info(f"Created {len(chunks)} chunks from {file_path.name}")
            
            # Process chunks
            processed_contents = []
            vectors = []
            
            for chunk_data in chunks:
                # Create RichmondContent object
                content_obj = RichmondContent(
                    source_file=file_path.name,
                    content_type=content_type,
                    content=chunk_data["content"],
                    chunk_index=chunk_data["chunk_index"],
                    total_chunks=len(chunks),
                    metadata=chunk_data.get("metadata", {})
                )
                
                # Generate embedding
                embedding = self.embedder.generate_embedding(chunk_data["content"])
                
                if embedding:
                    # Create vector ID
                    vector_id = f"{content_type}_{content_obj.content_id}"
                    content_obj.embedding_id = vector_id
                    
                    # Prepare for vector index
                    vector_metadata = {
                        "content_id": content_obj.content_id,
                        "content_type": content_type,
                        "source_file": file_path.name,
                        "chunk_index": chunk_data["chunk_index"],
                        **chunk_data.get("metadata", {})
                    }
                    
                    vectors.append((vector_id, embedding, vector_metadata))
                    processed_contents.append(content_obj)
                    self.stats["embeddings_generated"] += 1
                else:
                    logger.warning(f"Failed to generate embedding for chunk {chunk_data['chunk_index']}")
                    self.stats["errors"] += 1
            
            # Save to database
            if processed_contents:
                saved = self.content_repo.save_batch(processed_contents)
                logger.info(f"Saved {saved} content chunks to database")
                
                # Cache frequently accessed content
                if content_type in ["quotes", "culture"]:
                    entity_cache.set_content_batch(processed_contents[:10])
            
            # Index vectors
            if vectors:
                result = self.vector_manager.upsert_vectors(vectors)
                self.stats["vectors_indexed"] += result["upserted"]
                logger.info(f"Indexed {result['upserted']} vectors")
            
            # Mark file as processed
            self._mark_processed(file_path)
            
            self.stats["files_processed"] += 1
            self.stats["chunks_created"] += len(chunks)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process file {file_path.name}: {e}")
            self.stats["errors"] += 1
            self._mark_failed(file_path, str(e))
            return False
    
    def _get_content_type(self, filename: str) -> str:
        """Determine content type from filename"""
        filename_lower = filename.lower()
        
        if "quotes" in filename_lower:
            return "quotes"
        elif "culture" in filename_lower:
            return "culture"
        elif "economy" in filename_lower or "economic" in filename_lower:
            return "economy"
        elif "stories" in filename_lower or "story" in filename_lower:
            return "stories"
        elif "news" in filename_lower:
            return "news"
        else:
            return "general"
    
    def _mark_processed(self, file_path: Path):
        """Mark file as processed"""
        processed_path = Path(self.config.processed_dir) / f"{file_path.name}.processed"
        processed_path.write_text(f"Processed at: {datetime.utcnow().isoformat()}")
    
    def _mark_failed(self, file_path: Path, error: str):
        """Mark file as failed"""
        failed_path = Path(self.config.failed_dir) / f"{file_path.name}.failed"
        failed_path.write_text(f"Failed at: {datetime.utcnow().isoformat()}\nError: {error}")
    
    def _finalize_stats(self) -> Dict[str, Any]:
        """Finalize and return pipeline statistics"""
        self.stats["end_time"] = datetime.utcnow()
        
        if self.stats["start_time"] and self.stats["end_time"]:
            duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            self.stats["duration_seconds"] = duration
            self.stats["processing_rate"] = {
                "files_per_second": self.stats["files_processed"] / duration if duration > 0 else 0,
                "chunks_per_second": self.stats["chunks_created"] / duration if duration > 0 else 0
            }
        
        return self.stats
    
    async def update_content(self, file_path: Path) -> bool:
        """Update existing content (incremental update)"""
        logger.info(f"Updating content from: {file_path.name}")
        
        try:
            # Delete existing content and vectors
            content_type = self._get_content_type(file_path.name)
            existing_content = self.content_repo.list_by_type(content_type)
            
            # Filter to this source file
            file_content = [c for c in existing_content if c.source_file == file_path.name]
            
            if file_content:
                # Delete from vector index
                vector_ids = [c.embedding_id for c in file_content if c.embedding_id]
                if vector_ids:
                    self.vector_manager.delete_vectors(vector_ids)
                
                # Delete from database
                for content in file_content:
                    self.content_repo.delete(content.content_id)
                
                logger.info(f"Removed {len(file_content)} existing chunks")
            
            # Process the updated file
            return await self._process_file(file_path)
            
        except Exception as e:
            logger.error(f"Failed to update content: {e}")
            return False
    
    def validate_pipeline(self) -> Dict[str, Any]:
        """Validate pipeline components"""
        validation_results = {
            "bedrock_connection": False,
            "pinecone_connection": False,
            "database_connection": False,
            "data_directory": False,
            "errors": []
        }
        
        # Test Bedrock connection
        try:
            test_embedding = self.embedder.generate_embedding("test")
            validation_results["bedrock_connection"] = test_embedding is not None
        except Exception as e:
            validation_results["errors"].append(f"Bedrock error: {str(e)}")
        
        # Test Pinecone connection
        try:
            stats = self.vector_manager.index.describe_index_stats()
            validation_results["pinecone_connection"] = True
            validation_results["pinecone_stats"] = {
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension
            }
        except Exception as e:
            validation_results["errors"].append(f"Pinecone error: {str(e)}")
        
        # Test database connection
        try:
            self.content_repo.list_by_type("test", limit=1)
            validation_results["database_connection"] = True
        except Exception as e:
            validation_results["errors"].append(f"Database error: {str(e)}")
        
        # Check data directory
        data_path = Path(self.config.data_dir)
        if data_path.exists():
            md_files = list(data_path.glob("*.md"))
            validation_results["data_directory"] = True
            validation_results["markdown_files"] = len(md_files)
        else:
            validation_results["errors"].append(f"Data directory not found: {self.config.data_dir}")
        
        return validation_results


# Pipeline monitoring and metrics
class PipelineMonitor:
    """Monitor pipeline performance and health"""
    
    def __init__(self, pipeline: DataPipeline):
        self.pipeline = pipeline
        self.metrics = []
    
    def record_run(self, stats: Dict[str, Any]):
        """Record pipeline run metrics"""
        self.metrics.append({
            "timestamp": datetime.utcnow(),
            "stats": stats
        })
        
        # Keep only last 100 runs
        if len(self.metrics) > 100:
            self.metrics = self.metrics[-100:]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get pipeline performance summary"""
        if not self.metrics:
            return {"message": "No pipeline runs recorded"}
        
        # Calculate averages
        total_runs = len(self.metrics)
        successful_runs = sum(1 for m in self.metrics if m["stats"].get("errors", 0) == 0)
        
        avg_files = sum(m["stats"].get("files_processed", 0) for m in self.metrics) / total_runs
        avg_chunks = sum(m["stats"].get("chunks_created", 0) for m in self.metrics) / total_runs
        avg_duration = sum(m["stats"].get("duration_seconds", 0) for m in self.metrics) / total_runs
        
        return {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "success_rate": successful_runs / total_runs if total_runs > 0 else 0,
            "averages": {
                "files_per_run": avg_files,
                "chunks_per_run": avg_chunks,
                "duration_seconds": avg_duration
            },
            "last_run": self.metrics[-1]["stats"] if self.metrics else None
        }


# Convenience function for running pipeline
async def run_ingestion_pipeline(data_dir: Optional[str] = None) -> Dict[str, Any]:
    """Run the complete ingestion pipeline"""
    config = PipelineConfig()
    if data_dir:
        config.data_dir = data_dir
    
    pipeline = DataPipeline(config)
    monitor = PipelineMonitor(pipeline)
    
    # Validate pipeline first
    validation = pipeline.validate_pipeline()
    if validation["errors"]:
        logger.error(f"Pipeline validation failed: {validation['errors']}")
        return {"success": False, "validation": validation}
    
    # Run pipeline
    stats = await pipeline.process_directory()
    
    # Record metrics
    monitor.record_run(stats)
    
    return {
        "success": stats["errors"] == 0,
        "stats": stats,
        "validation": validation,
        "summary": monitor.get_summary()
    }