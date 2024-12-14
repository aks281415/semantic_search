# app/routes/search_routes.py
from flask import Blueprint, jsonify, request
from ..services.search_service import SearchService

search_bp = Blueprint('search', __name__)

@search_bp.route('/', methods=['POST'])
async def search():
    try:
        query = request.json.get('query')
        if not query:
            return jsonify({"error": "No query provided"}), 400
            
        search_service = SearchService()
        results = await search_service.search(query)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@search_bp.route('/health', methods=['GET'])
async def health_check():
    try:
        search_service = SearchService()
        status = await search_service.health_check()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500