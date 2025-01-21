import base64
import binascii
import json
import os
from typing import Optional, Dict, Any, Literal, List

import boto3
from mypy_boto3_secretsmanager.type_defs import GetSecretValueResponseTypeDef

from utils.constants import ENVIRONMENT_ENV, GCP_SERVICE_ACCOUNT_FILE_PATH_ENV, LANGCHAIN_API_KEY_ENV, \
    GITHUB_APP_PRIVATE_KEY_FILE_PATH_ENV, GITHUB_APP_PRIVATE_KEY_ENV, AZURE_OPENAI_API_KEY_ENV, AWS_SECRET_NAME_ENV, \
    AWS_SECRET_REGION_ENV, AWS_GCP_SA_SECRET_NAME_ENV, GITHUB_WEBHOOK_SECRET_ENV
from utils.logging_config import logger as log


class SecretManager:

    def __init__(self, mandatory_secrets: Optional[List[Literal["gcp", "openai", "langchain"]]] = None):
        if mandatory_secrets is None:
            mandatory_secrets = []

        self.__mandatory_secrets = mandatory_secrets

        self.__github_app_private_key: str
        self.__github_webhook_secret: str
        self.__gcp_credentials: Optional[str] = None
        self.__langchain_api_key: Optional[str] = None
        self.__azure_openai_api_key: Optional[str] = None

        self.__client: Any = None

        self.__secrets_cache: Optional[Dict[str, str]] = None

        self.__init_secrets()

    @property
    def github_app_private_key(self) -> str:
        return self.__github_app_private_key

    @property
    def github_webhook_secret(self) -> str:
        return self.__github_webhook_secret

    @property
    def gcp_credentials(self) -> Optional[str]:
        return self.__gcp_credentials

    @property
    def langchain_api_key(self) -> Optional[str]:
        return self.__langchain_api_key

    @property
    def azure_openai_api_key(self) -> Optional[str]:
        return self.__azure_openai_api_key

    def __init_secrets(self):
        try:
            self.__init_client()
        except Exception as e:
            if os.getenv(ENVIRONMENT_ENV) == "local":
                log.warning(f"Secrets Manager client cannot be initialized: {e}. Running in local environment.")
            else:
                raise ValueError(f"Error while initializing Secrets Manager client: {e}")

        try:
            self.__init_gcp_credentials()
            self.__init_azure_openai_api_key()
            self.__init_github_app_private_key()
            self.__init_github_webhook_secret()
            self.__init_langchain_api_key()
        except Exception as e:
            raise ValueError(f"Error while initializing secrets: {e}") from e

    def __init_gcp_credentials(self):
        log.debug("Initializing GCP service account credentials...")
        log.debug("Checking file...")
        credentials = self.__get_secret_from_file(GCP_SERVICE_ACCOUNT_FILE_PATH_ENV)
        if credentials:
            self.__gcp_credentials = credentials
            return

        log.debug("Fetching from Secrets Manager...")
        try:
            self.__gcp_credentials = self.__fetch_gcp_secret()
            return
        except Exception as e:
            log.debug(f"Error while fetching GCP service account credentials from Secrets Manager: {e}")

        if self.__mandatory_secrets and "gcp" in self.__mandatory_secrets:
            raise ValueError("GCP service account credentials cannot be initialized")

    def __init_langchain_api_key(self):
        if os.getenv(ENVIRONMENT_ENV) == "local":
            return

        log.debug("Initializing Langchain API key...")
        log.debug("Checking environment variable...")
        secret = self.__get_secret_from_env_var(LANGCHAIN_API_KEY_ENV)
        if secret:
            self.__langchain_api_key = secret
            return

        log.debug("Fetching from Secrets Manager...")
        try:
            self.__langchain_api_key = self.__get_secret_from_secret_manager("langchain_api_key")
            return
        except Exception as e:
            log.debug(f"Error while fetching Langchain API key from Secrets Manager: {e}")

        if self.__mandatory_secrets and "langchain" in self.__mandatory_secrets:
            raise ValueError("Langchain API key cannot be initialized")

    def __init_github_app_private_key(self):
        log.debug("Initializing GitHub App private key secret...")
        log.debug("Checking file...")
        secret = self.__get_secret_from_file(GITHUB_APP_PRIVATE_KEY_FILE_PATH_ENV)
        if secret:
            self.__github_app_private_key = secret
            return

        log.debug("Checking environment variable...")
        secret = self.__get_secret_from_env_var(GITHUB_APP_PRIVATE_KEY_ENV, "base64")
        if secret:
            self.__github_app_private_key = secret
            return

        log.debug("Fetching GitHub App private key from Secrets Manager...")
        try:
            self.__github_app_private_key = self.__get_secret_from_secret_manager("github_app_private_key",
                                                                                  encoding="base64")
            return
        except Exception as e:
            log.debug(f"Error while fetching GitHub App private key from Secrets Manager: {e}")

        raise ValueError("GitHub App private key cannot be initialized")

    def __init_github_webhook_secret(self):
        log.debug("Initializing GitHub webhook secret...")
        log.debug("Checking environment variable...")
        secret = self.__get_secret_from_env_var(GITHUB_WEBHOOK_SECRET_ENV)
        if secret:
            self.__github_webhook_secret = secret
            return

        log.debug("Fetching from Secrets Manager...")
        try:
            self.__github_webhook_secret = self.__get_secret_from_secret_manager("github_webhook_secret")
            return
        except Exception as e:
            log.debug(f"Error while fetching GitHub webhook secret from Secrets Manager: {e}")

        raise ValueError("GitHub webhook secret cannot be initialized")

    def __init_azure_openai_api_key(self):
        log.debug("Initializing Azure OpenAI API key secret...")
        log.debug("Checking environment variable...")
        secret = self.__get_secret_from_env_var(AZURE_OPENAI_API_KEY_ENV)
        if secret:
            self.__azure_openai_api_key = secret
            return

        log.debug("Fetching from Secrets Manager...")
        try:
            self.__azure_openai_api_key = self.__get_secret_from_secret_manager("azure_openai_api_key")
            return
        except Exception as e:
            log.debug(f"Error while fetching Azure OpenAI API key from Secrets Manager: {e}")

        if self.__mandatory_secrets and "openai" in self.__mandatory_secrets:
            raise ValueError("Azure OpenAI API key cannot be initialized")

    def __fetch_gcp_secret(self) -> str:
        secret_name = os.getenv(AWS_GCP_SA_SECRET_NAME_ENV)
        if not secret_name:
            raise EnvironmentError("Missing required environment variables for GCP service account secret.")

        log.debug("Pulling GCP service account secret from AWS Secrets Manager...")
        if not self.__client:
            raise ValueError("Client not initialized")

        try:
            get_secret_value_response: GetSecretValueResponseTypeDef = self.__client.get_secret_value(
                SecretId=secret_name)
        except Exception:
            raise

        secret: str = get_secret_value_response.get("SecretString", "")
        if not secret:
            raise ValueError("Got invalid GCP service account credentials from Secrets Manager")

        return secret

    def __fetch_secrets(self) -> dict[str, str]:
        if self.__secrets_cache is not None:
            return self.__secrets_cache

        secret_name = os.getenv(AWS_SECRET_NAME_ENV)
        if not secret_name:
            raise EnvironmentError("Missing required environment variables for secrets.")

        log.debug("Pulling secrets...")
        if not self.__client:
            raise ValueError("Client not initialized")
        get_secret_value_response: GetSecretValueResponseTypeDef = self.__client.get_secret_value(SecretId=secret_name)

        secret: str = get_secret_value_response.get("SecretString")
        if not secret:
            raise ValueError("Got invalid secret from AWS Secrets Manager")
        try:
            secrets_dict = json.loads(secret)
            self.__secrets_cache = secrets_dict
        except Exception as e:
            raise ValueError(f"Error while decoding secret: {e}")

        return secrets_dict

    def __init_client(self):
        region = os.getenv(AWS_SECRET_REGION_ENV)
        if not region:
            raise EnvironmentError("Missing required environment variables for secrets.")
        self.__client = boto3.client(service_name="secretsmanager", region_name=region)

    def __get_secret_from_secret_manager(self, secret_field: str, encoding: Optional[Literal["base64"]] = None) -> str:
        try:
            secrets = self.__fetch_secrets()
        except Exception as e:
            raise ValueError(f"Error while fetching secrets: {e}")

        secret = secrets.get(secret_field, "")
        if not secret:
            raise ValueError(f"Secret {secret_field} not found in secrets")

        if encoding and encoding == "base64":
            return self.__decode_base64(secret)

        return secret

    def __get_secret_from_env_var(self, env_var: str, encoding: Optional[Literal["base64"]] = None) -> str:
        secret = os.getenv(env_var)
        if not secret:
            return ""

        if encoding and encoding == "base64":
            return self.__decode_base64(secret)

        return secret

    @staticmethod
    def __get_secret_from_file(path_env_var: str) -> str:
        file_path = os.getenv(path_env_var)
        if not file_path or not os.path.isfile(file_path):
            return ""

        try:
            with open(file_path) as f:
                secret = f.read()
                return secret
        except OSError:
            return ""

    @staticmethod
    def __decode_base64(secret: str) -> str:
        try:
            secret_bytes = base64.b64decode(secret)
            return secret_bytes.decode()
        except binascii.Error:
            return ""


if os.getenv("TESTENV") != "true":
    secret_manager = SecretManager(mandatory_secrets=["openai", "langchain"])
else:
    secret_manager = None
