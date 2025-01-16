import os

from utils.constants import ENVIRONMENT_ENV, LANGCHAIN_API_KEY_ENV
from utils.secret_manager import secret_manager


def set_environment_variables():
    if os.getenv(ENVIRONMENT_ENV) == "local":
        return

    os.environ[LANGCHAIN_API_KEY_ENV] = secret_manager.get_langchain_api_key()
