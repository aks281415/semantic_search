import os
import json 
import uuid
import logging
from typing import Dict, List, Generator
from PyPDF2 import PdfReader
from config import config
from concurrent.futures import ThreadPoolExecutor
from functools import partial

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('document_processing.log')
    ]
)
logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        self.config = config[os.getenv('FLASK_ENV','default')]
        self.pdf_dir = self.config.PDF_DIR
        self.metadata_path = self.config.METADATA_PATH
        self.chunk_size = self.config.CHUNK_SIZE
        self.chunk_overlap = self.config.CHUNK_OVERLAP
        self.max_workers = self.config.MAX_WORKERS  # Add to config: typically 5-10
        self.batch_size = self.config.BATCH_SIZE    # Add to config: typically 5

    def load_metadata(self) -> List[Dict]:
        try:
            with open(self.metadata_path, 'r') as f:
                metadata = json.load(f)
            logger.info(f"Successfully loaded metadata for {len(metadata)} documents")
            return metadata
        except Exception as e:
            logger.error(f"Failed to load metadata: {str(e)}")
            raise

    def load_pdf_content(self, pdf_path: str) -> str:
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            logger.info(f"Successfully extracted text from {pdf_path}")
            return text
        except Exception as e:
            logger.error(f"Error reading PDF {pdf_path}: {str(e)}")
            raise

    def process_single_document(self, filename: str, metadata: List[Dict]) -> Dict:
        """Process a single PDF document"""
        try:
            if not filename.endswith('.pdf'):
                return None
            
            pdf_path = os.path.join(self.pdf_dir, filename)
            doc_metadata = next((m for m in metadata if m['filename'] == filename), None)
            
            if not doc_metadata:
                logger.warning(f"No metadata found for {filename}")
                return None

            content = self.load_pdf_content(pdf_path)
            logger.info(f"Successfully processed document: {filename}")
            return {'content': content, 'metadata': doc_metadata}
            
        except Exception as e:
            logger.error(f"Error processing document {filename}: {str(e)}")
            return None

    async def process_documents_parallel(self) -> List[Dict]:
        """Process PDFs in parallel"""
        try:
            metadata = self.load_metadata()
            filenames = [f for f in os.listdir(self.pdf_dir) if f.endswith('.pdf')]
            documents = []

            logger.info(f"Starting parallel processing of {len(filenames)} documents")
            
            # Process documents in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Create partial function with metadata
                process_doc = partial(self.process_single_document, metadata=metadata)
                
                # Process files in parallel
                futures = list(executor.map(process_doc, filenames))
                
                # Filter out None results and extend documents
                documents.extend([doc for doc in futures if doc is not None])

            logger.info(f"Successfully processed {len(documents)} documents in parallel")
            return documents

        except Exception as e:
            logger.error(f"Error in parallel document processing: {str(e)}")
            raise

    def create_chunks(self, text: str, metadata: Dict) -> List[Dict]:
        """Create chunks from text with metadata"""
        try:
            chunks = []
            start = 0
            chunk_index = 0

            while start < len(text):
                end = start + self.chunk_size
                if start > 0:
                    start = start - self.chunk_overlap
                
                chunk_text = text[start:end]
                
                chunk = {
                    "chunk_id": str(uuid.uuid4()),
                    "content": chunk_text,
                    "metadata": {
                        **metadata,
                        "chunk_index": chunk_index,
                        "is_first_chunk": chunk_index == 0,
                        "chunk_start": start,
                        "chunk_end": end
                    }
                }
                
                chunks.append(chunk)
                start = end
                chunk_index += 1

            logger.info(f"Created {len(chunks)} chunks for document: {metadata.get('filename')}")
            return chunks

        except Exception as e:
            logger.error(f"Error creating chunks for document {metadata.get('filename')}: {str(e)}")
            raise

    async def process_chunks_in_batches(self, documents: List[Dict]) -> Generator[Dict, None, None]:
        """Process document chunks in batches"""
        try:
            total_chunks = []
            
            for i in range(0, len(documents), self.batch_size):
                batch = documents[i:i + self.batch_size]
                logger.info(f"Processing batch {i//self.batch_size + 1}")
                
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # Process each document in the batch
                    futures = [
                        executor.submit(self.create_chunks, doc['content'], doc['metadata'])
                        for doc in batch
                    ]
                    
                    # Collect results
                    for future in futures:
                        try:
                            chunks = future.result()
                            total_chunks.extend(chunks)
                        except Exception as e:
                            logger.error(f"Error processing chunk batch: {str(e)}")

            logger.info(f"Successfully processed all chunks. Total chunks: {len(total_chunks)}")
            return total_chunks

        except Exception as e:
            logger.error(f"Error in batch chunk processing: {str(e)}")
            raise

    async def process_all(self) -> List[Dict]:
        """Main method to process all documents and chunks"""
        try:
            logger.info("Starting document processing pipeline")
            
            # Process documents in parallel
            documents = await self.process_documents_parallel()
            
            # Process chunks in batches
            chunks = await self.process_chunks_in_batches(documents)
            
            logger.info("Completed document processing pipeline")
            return chunks

        except Exception as e:
            logger.error(f"Error in document processing pipeline: {str(e)}")
            raise