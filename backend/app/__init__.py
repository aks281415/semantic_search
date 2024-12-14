# app/__init__.py
from flask import Flask
from flask_cors import CORS
from .routes import register_routes
from .middleware import register_middleware
from .middleware.error_handlers import register_error_handlers

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Register components
    register_routes(app)
    register_middleware(app)
    register_error_handlers(app)
    
    return app