import asyncio
import logging
import os
import traceback

try:
    from app.services.document_service import DocumentService
    from app.services.bootstrap_service import BootstrapService
    from app.services.search_service import SearchService
    print("Services imported successfully")
except Exception as e:
    print(f"Critical error during imports: {e}")
    print(traceback.format_exc())
    exit(1)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG level for maximum verbosity
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_document_service():
    logger.info("Entered test_document_service function")
    try:
        logger.debug("Initializing DocumentService")
        doc_service = DocumentService()
        logger.debug("DocumentService initialized successfully")
        print(f"DocumentService initialized: {doc_service}")
    except Exception as e:
        logger.error(f"Error initializing DocumentService: {e}")
        print(traceback.format_exc())
        return

    # Test loading metadata
    try:
        logger.debug("Attempting to load metadata")
        metadata = doc_service.load_metadata()
        logger.info(f"Loaded metadata: {len(metadata)} entries")
        print(f"Metadata loaded: {metadata}")
    except Exception as e:
        logger.error(f"Error loading metadata: {e}")
        print(traceback.format_exc())

    # Test processing single document
    try:
        logger.debug(f"Looking for PDFs in directory: {doc_service.pdf_dir}")
        if not os.path.exists(doc_service.pdf_dir):
            logger.error(f"PDF directory does not exist: {doc_service.pdf_dir}")
            print(f"PDF directory does not exist: {doc_service.pdf_dir}")
            return

        pdfs = [f for f in os.listdir(doc_service.pdf_dir) if f.endswith('.pdf')]
        logger.debug(f"Found PDFs: {pdfs}")
        print(f"PDFs found: {pdfs}")

        if pdfs:
            logger.debug(f"Processing first document: {pdfs[0]}")
            document = doc_service.process_single_document(pdfs[0], metadata)
            logger.info(f"Processed document: {document['metadata']['filename']}")
            print(f"Processed document: {document}")
        else:
            logger.warning("No PDFs found in the directory")
            print("No PDFs found in the directory")
    except Exception as e:
        logger.error(f"Error processing single document: {e}")
        print(traceback.format_exc())

async def test_bootstrap_service():
    logger.info("Entered test_bootstrap_service function")
    try:
        logger.debug("Initializing BootstrapService")
        bootstrap_service = BootstrapService()
        logger.debug("BootstrapService initialized successfully")
        print(f"BootstrapService initialized: {bootstrap_service}")
    except Exception as e:
        logger.error(f"Error initializing BootstrapService: {e}")
        print(traceback.format_exc())
        return

    # Test bootstrap process
    try:
        logger.debug("Starting bootstrap process")
        results = await bootstrap_service.bootstrap()
        logger.info(f"Bootstrap completed. Stats: {results['stats']}")
        print(f"Bootstrap results: {results}")
    except Exception as e:
        logger.error(f"Error in bootstrap process: {e}")
        print(traceback.format_exc())

async def test_search_service():
    logger.info("Entered test_search_service function")
    try:
        logger.debug("Initializing SearchService")
        search_service = SearchService()
        logger.debug("SearchService initialized successfully")
        print(f"SearchService initialized: {search_service}")
    except Exception as e:
        logger.error(f"Error initializing SearchService: {e}")
        print(traceback.format_exc())
        return

    # Test creating embeddings
    try:
        query = "Example legal query"
        logger.debug(f"Creating embedding for query: {query}")
        embedding = await search_service.create_embedding(query)
        if embedding:
            logger.info(f"Successfully created embedding for query: {query}")
            print(f"Embedding created: {embedding}")
        else:
            logger.warning("Embedding creation returned None")
            print("Embedding creation returned None")
    except Exception as e:
        logger.error(f"Error creating embedding: {e}")
        print(traceback.format_exc())

    # Test search functionality
    try:
        query = "Example legal query"
        logger.debug(f"Searching with query: {query}")
        search_results = await search_service.search_with_timeout(query, top_k=5)
        logger.info(f"Search results: {search_results['results']}")
        print(f"Search results: {search_results}")
    except Exception as e:
        logger.error(f"Error in search functionality: {e}")
        print(traceback.format_exc())

    # Test health check
    try:
        logger.debug("Performing health check")
        health_status = await search_service.health_check()
        logger.info(f"SearchService health status: {health_status}")
        print(f"Health check status: {health_status}")
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        print(traceback.format_exc())

async def run_tests():
    logger.info("Starting all tests...")
    print("Starting all tests...")
    try:
        await test_document_service()
    except Exception as e:
        logger.error(f"Error during DocumentService tests: {e}")
        print(traceback.format_exc())

    try:
        await test_bootstrap_service()
    except Exception as e:
        logger.error(f"Error during BootstrapService tests: {e}")
        print(traceback.format_exc())

    try:
        await test_search_service()
    except Exception as e:
        logger.error(f"Error during SearchService tests: {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    print("Starting script...")
    logger.info("Starting local tests...")
    try:
        logger.debug("About to run asyncio loop")
        asyncio.run(run_tests())
        logger.info("Completed running tests")
        print("Completed running tests")
    except Exception as e:
        logger.critical(f"Critical error in main execution: {e}")
        print(traceback.format_exc())
