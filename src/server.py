"""HTTP server for Cloud Run deployment."""
import logging
import os
from datetime import datetime
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from src.main import PeopleDataExporter
from src.auth import require_auth, optional_auth

app = Flask(__name__)
logger = logging.getLogger(__name__)


@app.route('/health', methods=['GET'])
@optional_auth
def health_check():
    """
    Health check endpoint.
    
    Returns 200 if service is healthy and can accept requests.
    Authentication is optional for this endpoint.
    """
    user = getattr(request, 'user_email', None)
    
    response = {
        'status': 'healthy',
        'service': 'people-data-exporter',
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if user:
        response['authenticated_user'] = user
    
    return jsonify(response), 200


@app.route('/sync', methods=['POST'])
@require_auth
def trigger_sync():
    """
    Trigger the data sync process.
    
    Requires authentication and Cloud Run Invoker permission.
    
    Returns:
        200: Sync completed successfully
        401: Unauthorized (invalid or missing token)
        403: Forbidden (insufficient permissions)
        500: Sync failed
    """
    start_time = datetime.utcnow()
    user_email = getattr(request, 'user_email', 'unknown')
    
    logger.info(f"Sync triggered via HTTP endpoint by user: {user_email}")
    
    try:
        exporter = PeopleDataExporter()
        exporter.run()
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return jsonify({
            'status': 'success',
            'message': 'Data sync completed successfully',
            'triggered_by': user_email,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration
        }), 200
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return jsonify({
            'status': 'error',
            'error_type': 'configuration_error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500
        
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error_type': 'sync_error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@app.route('/', methods=['GET'])
def root():
    """Root endpoint with service information."""
    return jsonify({
        'service': 'people-data-exporter',
        'version': '1.0.0',
        'endpoints': {
            'health': '/health',
            'sync': '/sync (POST)'
        }
    }), 200


@app.errorhandler(HTTPException)
def handle_http_exception(e):
    """Handle HTTP exceptions."""
    return jsonify({
        'status': 'error',
        'error': e.name,
        'message': e.description
    }), e.code


@app.errorhandler(Exception)
def handle_exception(e):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return jsonify({
        'status': 'error',
        'error': 'internal_server_error',
        'message': 'An unexpected error occurred'
    }), 500


def main():
    """Start the HTTP server."""
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"Starting HTTP server on port {port}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )


if __name__ == '__main__':
    main()

