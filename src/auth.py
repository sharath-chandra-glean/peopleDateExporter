"""Authentication and authorization for Cloud Run deployment."""
import logging
import os
from functools import wraps
from typing import Optional

from flask import request, jsonify
from google.auth.transport import requests as google_requests
from google.cloud import resourcemanager_v3
from google.iam.v1 import iam_policy_pb2
import google.auth


logger = logging.getLogger(__name__)

# Cache the project ID after first retrieval
_cached_project_id: Optional[str] = None


def get_project_id() -> str:
    """
    Get the GCP project ID from the Cloud Run environment.
    
    Cloud Run automatically sets the project context. This function
    retrieves it from the application default credentials.
    
    Returns:
        The GCP project ID where the Cloud Run service is running
        
    Raises:
        RuntimeError: If project ID cannot be determined
    """
    global _cached_project_id
    
    if _cached_project_id:
        return _cached_project_id
    
    try:
        _, project_id = google.auth.default()
        if project_id:
            _cached_project_id = project_id
            logger.info(f"Detected GCP project ID: {project_id}")
            return project_id
    except Exception as e:
        logger.warning(f"Could not detect project from default credentials: {e}")
    
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('GCP_PROJECT') or os.environ.get('GCLOUD_PROJECT')
    if project_id:
        _cached_project_id = project_id
        logger.info(f"Using project ID from environment: {project_id}")
        return project_id
    
    raise RuntimeError(
        "Unable to determine GCP project ID. This service must run in a GCP environment "
        "(Cloud Run, GCE, GKE, etc.) where the project context is automatically available."
    )


class AuthError(Exception):
    """Custom exception for authentication errors."""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def verify_token(token: str) -> dict:
    """
    Verify and decode Google Cloud access token.
    
    Args:
        token: The Bearer token from Authorization header
        
    Returns:
        Token info containing user information
        
    Raises:
        AuthError: If token is invalid or verification fails
    """
    try:
        # Use TokenInfo API to verify access token
        request_adapter = google_requests.Request()
        
        # Call Google's tokeninfo endpoint to verify the access token
        response = request_adapter(
            url=f'https://oauth2.googleapis.com/tokeninfo?access_token={token}',
            method='GET'
        )
        
        if response.status != 200:
            raise ValueError(f"Token verification failed with status {response.status}")
        
        import json
        token_info = json.loads(response.data.decode('utf-8'))
        
        # Verify token has not expired
        if 'error' in token_info:
            raise ValueError(f"Invalid token: {token_info.get('error_description', 'Unknown error')}")
        
        # Check if token has required scope (optional but recommended)
        scopes = token_info.get('scope', '').split()
        logger.debug(f"Token scopes: {scopes}")
        
        email = token_info.get('email')
        if not email:
            raise ValueError("Token does not contain email information")
        
        logger.debug(f"Access token verified for email: {email}")
        return token_info
        
    except ValueError as e:
        logger.warning(f"Access token verification failed: {e}")
        raise AuthError("Invalid authentication token", 401)
    except Exception as e:
        logger.error(f"Access token verification error: {e}")
        raise AuthError("Authentication failed", 401)


def check_cloud_run_invoker_permission(email: str, project_id: str) -> bool:
    """
    Check if user has Cloud Run Invoker permission in the project.
    
    Args:
        email: User's email address
        project_id: GCP project ID
        
    Returns:
        True if user has permission, False otherwise
    """
    logger.info(f"Checking IAM permissions for {email} in project {project_id}")
    try:
        
        client = resourcemanager_v3.ProjectsClient()
        
        resource = f"projects/{project_id}"

        logger.info(f"IAM permissions resource: {resource}")
        
        request_obj = iam_policy_pb2.TestIamPermissionsRequest(
            resource=resource,
            permissions=["run.routes.invoke"]
        )
        
        logger.info(f"IAM permissions request: {request_obj}")
        
        response = client.test_iam_permissions(request=request_obj)

        logger.info(f"IAM permissions response: {response}")
        
        has_permission = "run.routes.invoke" in response.permissions
        
        if has_permission:
            logger.info(f"User {email} has Cloud Run Invoker permission")
        else:
            logger.warning(f"User {email} does NOT have Cloud Run Invoker permission")
            
        return has_permission
        
    except Exception as e:
        logger.error("IN here")
        logger.error(f"Failed to check IAM permissions: {e}")
        return False


def extract_token_from_header() -> Optional[str]:
    """
    Extract bearer token from Authorization header.
    
    Returns:
        The token string or None if not found
    """
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header:
        return None
    
    parts = auth_header.split()
    
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]


def require_auth(f):
    """
    Decorator to require authentication and authorization for endpoints.
    
    Verifies:
    1. Valid Google Cloud access token is provided
    2. User has Cloud Run Invoker permission in the project
    
    Usage:
        @app.route('/protected')
        @require_auth
        def protected_endpoint():
            return {'message': 'success'}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.info(f"Decorated function called: {f.__name__}")
        try:
            token = extract_token_from_header()
            
            if not token:
                logger.warning("No authorization token provided")
                return jsonify({
                    'status': 'error',
                    'error': 'unauthorized',
                    'message': 'Authorization token required. Please provide a Bearer token in the Authorization header.'
                }), 401
            
            token_info = verify_token(token)
            
            email = token_info.get('email')
            if not email:
                logger.warning("Token does not contain email")
                return jsonify({
                    'status': 'error',
                    'error': 'unauthorized',
                    'message': 'Invalid token: email not found'
                }), 401
            
            try:
                project_id = get_project_id()
            except RuntimeError as e:
                logger.error(f"Failed to get project ID: {e}")
                return jsonify({
                    'status': 'error',
                    'error': 'configuration_error',
                    'message': 'Server configuration error: unable to determine GCP project ID'
                }), 500
            
            logger.info(f"Checking IAM permissions for {email} in project {project_id}")

            has_permission = check_cloud_run_invoker_permission(email, project_id)
            
            if not has_permission:
                logger.warning(f"Access denied for {email}: insufficient permissions")
                return jsonify({
                    'status': 'error',
                    'error': 'forbidden',
                    'message': f'Access denied. User {email} does not have Cloud Run Invoker permission in project {project_id}.'
                }), 403
            
            logger.info(f"Access granted for {email}")
            
            request.user_email = email
            request.user_info = token_info
            
            return f(*args, **kwargs)
            
        except AuthError as e:
            return jsonify({
                'status': 'error',
                'error': 'unauthorized',
                'message': e.message
            }), e.status_code
            
        except Exception as e:
            logger.error(f"Authorization error: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': 'authorization_error',
                'message': 'Failed to verify authorization'
            }), 500
    
    return decorated_function


def optional_auth(f):
    """
    Decorator to optionally authenticate requests.
    
    If a token is provided, it will be verified, but if no token
    is provided, the request will still proceed. Useful for endpoints
    that should work both authenticated and unauthenticated.
    
    Usage:
        @app.route('/optional')
        @optional_auth
        def optional_endpoint():
            user = getattr(request, 'user_email', None)
            return {'user': user or 'anonymous'}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            token = extract_token_from_header()
            
            if token:
                token_info = verify_token(token)
                request.user_email = token_info.get('email')
                request.user_info = token_info
            else:
                request.user_email = None
                request.user_info = None
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.warning(f"Optional auth failed: {e}")
            request.user_email = None
            request.user_info = None
            return f(*args, **kwargs)
    
    return decorated_function

