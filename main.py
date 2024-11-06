import logging
from utils.logging_config import setup_console_logging, setup_file_logging
import functions_framework
import handle_pr

LOGGER_NAME = "prcoach"
logger = setup_console_logging(name=LOGGER_NAME, log_level=logging.DEBUG)

@functions_framework.http
def handle_event(request):

    print(f"got request {request}")
    try:
        payload = request.get_json(silent=True)
        x_github_event = request.headers.get('X-GitHub-Event')
        handle_pr.handle_github_event(payload, x_github_event, False)
        logger.info("success")
        return {'message': 'Success'}, 200
    except Exception as e:
        logger.error("error", e)
        return {'error': str(e)}, 500
