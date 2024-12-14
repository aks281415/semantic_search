# app/routes/bootstrap_routes.py
from flask import Blueprint, jsonify, current_app
from ..services.bootstrap_service import BootstrapService

bootstrap_bp = Blueprint('bootstrap', __name__)

@bootstrap_bp.route('/', methods=['POST'])
async def initialize_system():
    try:
        bootstrap_service = BootstrapService()
        result = await bootstrap_service.bootstrap()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bootstrap_bp.route('/status', methods=['GET'])
async def get_status():
    try:
        bootstrap_service = BootstrapService()
        status = await bootstrap_service.get_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500