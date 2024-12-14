import os
import openai
import pinecone
import logging
import time
import asyncio
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from cachetools import TTLCache
from config import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('search_service.log')
    ]
)
logger = logging.getLogger(__name__)

class SearchService:
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SearchService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.config = config[os.getenv('FLASK_ENV', 'default')]
            self.openai_api_key = self.config.OPENAI_API_KEY
            self.pinecone_api_key = self.config.PINECONE_API_KEY
            self.pinecone_env = self.config.PINECONE_ENV
            
            # Initialize connection pool
            self.initialize_connections()
            
            # Configure limits
            self.max_concurrent_searches = self.config.MAX_CONCURRENT_SEARCHES  # e.g., 50 ,update in config
            self.search_timeout = self.config.SEARCH_TIMEOUT  # e.g., 10 seconds , update in config
            
            # Cache configuration
            self.cache = TTLCache(
                maxsize=self.config.CACHE_SIZE,  # e.g., 1000
                ttl=self.config.CACHE_TTL  # e.g., 3600 seconds
            )
            
            # Semaphore for limiting concurrent requests
            self.semaphore = asyncio.Semaphore(self.max_concurrent_searches)
            
            self.initialized = True

    def initialize_connections(self):
        """Initialize and maintain connections"""
        try:
            openai.api_key = self.openai_api_key
            pinecone.init(
                api_key=self.pinecone_api_key,
                environment=self.pinecone_env
            )
            self.index = pinecone.Index(self.config.PINECONE_INDEX)
            logger.info("Connections initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize connections: {str(e)}")
            raise

    #@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=4))
    async def create_embedding(self, query: str) -> Optional[List[float]]:
        """Create embedding with retry logic"""
        try:
            response = await openai.embeddings.create(
                model="text-embedding-ada-002",
                input=query
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding creation failed: {str(e)}")
            raise

    async def search_with_timeout(self, query: str, top_k: int = None) -> Dict:
        """Execute search with timeout"""
        async with self.semaphore:  # Limit concurrent searches
            try:
                return await asyncio.wait_for(
                    self._execute_search(query, top_k),
                    timeout=self.search_timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Search timeout for query: {query}")
                raise TimeoutError("Search request timed out")

    async def _execute_search(self, query: str, top_k: int = None) -> Dict:
        """Core search logic"""
        start_time = time.time()
        
        # Check cache
        cache_key = f"{query}:{top_k}"
        if cache_key in self.cache:
            logger.info(f"Cache hit for query: {query}")
            return self.cache[cache_key]

        try:
            # Create embedding
            embedding = await self.create_embedding(query)
            
            # Search in Pinecone
            search_results = self.index.query(
                vector=embedding,
                top_k=top_k or self.config.DEFAULT_TOP_K,
                include_metadata=True
            )

            # Format results
            formatted_results = []
            for match in search_results.matches:
                formatted_results.append({
                    "content": match.metadata.get("content", ""),
                    "metadata": {
                        "case": match.metadata.get("case", ""),
                        "year": match.metadata.get("year", ""),
                        "court": match.metadata.get("court", ""),
                        "citation": match.metadata.get("citation", "")
                    },
                    "similarity_score": match.score
                })

            response = {
                "results": formatted_results,
                "total_results": len(formatted_results),
                "processing_time": f"{time.time() - start_time:.2f}s"
            }

            # Cache results
            self.cache[cache_key] = response
            return response

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise

    async def health_check(self) -> Dict:
        """Check service health"""
        try:
            # Test embedding creation
            test_embedding = await self.create_embedding("test")
            if not test_embedding:
                return {"status": "unhealthy", "error": "Embedding creation failed"}

            # Test Pinecone connection
            self.index.describe_index_stats()

            return {
                "status": "healthy",
                "cache_size": len(self.cache),
                "active_connections": self.semaphore._value
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}