import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Flask Config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-placeholder'
    DEBUG = os.environ.get('FLASK_ENV') == 'development'

    # File Paths
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    PDF_DIR = os.path.join(BASE_DIR,'app', 'docs', 'pdfs')
    METADATA_PATH = os.path.join(BASE_DIR,'app', 'docs', 'metadata.json')

    # API Keys
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
    PINECONE_ENV = os.environ.get('PINECONE_ENV')
    PINECONE_INDEX = os.environ.get('PINECONE_INDEX')

    # Chunking Configuration
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200  # Optional: If we want overlapping chunks

    # Search Configuration
    MAX_SEARCH_RESULTS = 5
    
    MAX_CONCURRENT_SEARCHES = 5
    SEARCH_TIMEOUT = 5
    CACHE_SIZE = 3
    CACHE_TTL = 60
    
    MAX_WORKERS = 3
    BATCH_SIZE = 3
    EMBEDDING_BATCH_SIZE = 3

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # Add production-specific settings here

# Map config names to config classes
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}