import time
from flask import request, g
import logging

logger = logging.getLogger(__name__)

def register_middleware(app):
    # Request Logger
    @app.before_request
    def log_request():
        g.start_time = time.time()
        logger.info(f"Incoming {request.method} request to {request.path}")

    # Response Logger
    @app.after_request
    def log_response(response):
        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time
            logger.info(f"Request completed in {elapsed:.2f}s with status {response.status_code}")
        return response

    # Rate Limiting
    @app.before_request
    def rate_limit():
        # Implement rate limiting logic here
        pass