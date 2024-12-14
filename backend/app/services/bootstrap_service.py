import os
import openai
import pinecone
import logging
import time
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
from .document_service import DocumentService
from config import config

# setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bootstrap_service.log')
    ]
)
logger = logging.getLogger(__name__)

class BootstrapService:
    def __init__(self):
        self.config = config[os.getenv('FLASK_ENV', 'default')]
        self.doc_service = DocumentService()
        
        # intitiaise openai
        openai.api_key = self.config.OPENAI_API_KEY
        
        # Service configs
        self.batch_size = self.config.EMBEDDING_BATCH_SIZE  # Add to config: typically 100
        self.max_workers = self.config.MAX_WORKERS         # Add to config: typically 5
        self.max_retries = 3
        
    async def check_embedding_status(self, chunk_id: str, index: Any) -> bool:
        """Check if embedding already exists for a chunk"""
        try:
            result = index.fetch([chunk_id])
            return bool(result.vectors)
        except Exception as e:
            logger.error(f"Error checking embedding status: {str(e)}")
            return False
        
    # @retry(stop_after_attempt(2), wait = wait_exponential(multiplier=1, min=2,max=4))
    async def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a batch of texts with retry logic"""
        try:
            response = await openai.embeddings.create(
                model="text-embedding-ada-002",
                input=texts
            )
            logger.info(f"Successfully created embeddings for batch of {len(texts)} texts")
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Error creating embeddings batch: {str(e)}")
            raise
        
    async def process_chunks_to_vectors(self, chunks: List[Dict], index: Any) -> List[Dict]:
        """Convert chunks to vectors with embeddings"""
        vectors = []
        
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            new_chunks = []
            new_chunks_texts = []
            
            # check which chunks need processing
            
            for chunk in batch:
                if not await self.check_embedding_status(chunk["chunk_id"]):
                    new_chunks.append(chunk)
                    new_chunks_texts.append(chunk["context"])
                else:
                    logger.info(f"Chunk {chunk['chunk_id']} already exists, skipping...")
                    
            if not new_chunks:
                continue
            
            try:
                # create embeddings only for new chunks
                if new_chunks_texts:
                    embeddings = await self.create_embeddings_batch(new_chunks_texts)
                    
                    # create vectors with embeddings and metadata
                    for chunk, embedding in zip(new_chunks, embeddings):
                        vector = {
                            "id": chunk["chunk_id"],
                            "values": embedding,
                            "metadata": {
                                **chunk["metadata"],
                                "content": chunk["content"],
                                "processed_at": time.time()
                            }
                        }
                    vectors.append(vector)
                    
                    logger.info(f"Processed batch {i//self.batch_size + 1}, "
                              f"new vectors: {len(vectors)}")
                    
            except Exception as e:
                logger.error(f"Error processing batch {i//self.batch_size + 1}: {str(e)}")
                continue
        
        return vectors
    
    #@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=4))
    async def upsert_vectors_batch(self, index: Any, vectors: List[Dict]) -> bool:
        """Upsert a batch of vectors to Pinecone with retry logic"""
        try:
            # Check for empty vectors
            if not vectors:
                logger.info("No vectors to upsert. Skipping upsert process.")
                return False
            
            # Proceed with upserting if vectors are not empty
            index.upsert(vectors=vectors)
            logger.info(f"Successfully upserted batch of {len(vectors)} vectors")
            return True
        except Exception as e:
            logger.error(f"Error upserting vectors batch: {str(e)}")
            raise

        
    async def initialize_or_validate_index(self) -> Any:
        """Initialize Pinecone index or validate existing one"""
        try:
            # Initialize Pinecone
            pinecone.init(
                api_key=self.config.PINECONE_API_KEY,
                environment=self.config.PINECONE_ENV
            )
            
            # Check if index exists
            if self.config.PINECONE_INDEX not in pinecone.list_indexes():
                logger.info(f"Creating new index: {self.config.PINECONE_INDEX}")
                pinecone.create_index(
                    name=self.config.PINECONE_INDEX,
                    dimension=1536,
                    metric='cosine'
                )
                # Wait for index to be ready
                time.sleep(7)
            
            index = pinecone.Index(self.config.PINECONE_INDEX)
            
            # Validate index
            stats = index.describe_index_stats()
            logger.info(f"Index stats: {stats}")
            
            return index
            
        except Exception as e:
            logger.error(f"Error initializing Pinecone index: {str(e)}")
            raise
        
    async def get_status(self) -> Dict:
        """Get current status of vector database"""
        try:
            pinecone.init(
                api_key=self.config.PINECONE_API_KEY,
                environment=self.config.PINECONE_ENV
            )
            
            if self.config.PINECONE_INDEX in pinecone.list_indexes():
                index = pinecone.Index(self.config.PINECONE_INDEX)
                stats = index.describe_index_stats()
                return {
                    "status": "active",
                    "vector_count": stats.total_vector_count,
                    "index_fullness": stats.index_fullness
                }
            
            return {"status": "index_not_found"}
            
        except Exception as e:
            logger.error(f"Error getting status: {str(e)}")
            return {"status": "error", "message": str(e)}
    
        
    async def bootstrap(self) -> Dict:
        """Main bootstrap process"""
        start_time = time.time()
        stats = {
            "chunks_processed": 0,
            "new_vectors_created": 0,
            "batches_processed": 0
        }
        
        try:
            # Initialize index
            index = await self.initialize_or_validate_index()
            
            # Get chunks from document service
            logger.info("Starting document processing")
            chunks = await self.doc_service.process_all()
            stats["chunks_processed"] = len(chunks)
            time.sleep(2)
            
            # Process chunks to vectors
            logger.info("Converting chunks to vectors")
            vectors = await self.process_chunks_to_vectors(chunks, index)
            stats["new_vectors_created"] = len(vectors)
            time.sleep(2)
            
            # Upsert vectors in batches
            if vectors:
                logger.info("Upserting vectors to Pinecone")
                for i in range(0, len(vectors), self.batch_size):
                    batch = vectors[i:i + self.batch_size]
                    await self.upsert_vectors_batch(index, batch)
                    stats["batches_processed"] += 1
            else:
                logger.info("No new vectors to upsert")
            
            execution_time = time.time() - start_time
            logger.info(f"Bootstrap completed in {execution_time:.2f} seconds")
            
            return {
                "status": "success",
                "stats": stats,
                "execution_time": execution_time
            }
            
        except Exception as e:
            logger.error(f"Bootstrap failed: {str(e)}")
            raise

                      
            
        
    
        
        
        
