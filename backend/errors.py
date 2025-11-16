import logging
from flask import jsonify

logger = logging.getLogger(__name__)


class APIError(Exception):
    status_code = 500
    public_message = "Internal server error"

    def __init__(self, message: str | None = None, status_code: int | None = None):
        super().__init__(message or self.public_message)
        if status_code is not None:
            self.status_code = status_code


class ValidationError(APIError):
    status_code = 400
    public_message = "Invalid request"


def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(err: APIError):
        logger.exception("APIError: %s", err)
        return jsonify({"error": err.public_message}), err.status_code

    @app.errorhandler(404)
    def handle_404(_):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def handle_405(_):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        logger.exception("Unexpected error: %s", err)
        return jsonify({"error": "Internal server error"}), 500


