import json
import os
from typing import Optional, Dict, Any

import boto3
from botocore.client import BaseClient
from mypy_boto3_secretsmanager.type_defs import GetSecretValueResponseTypeDef

from utils.constants import ENVIRONMENT_ENV, GCP_SERVICE_ACCOUNT_FILE_PATH_ENV, LANGCHAIN_API_KEY_ENV, \
    GITHUB_APP_PRIVATE_KEY_FILE_PATH_ENV, GITHUB_APP_PRIVATE_KEY_ENV, AZURE_OPENAI_API_KEY_ENV, AWS_SECRET_NAME_ENV, \
    AWS_SECRET_REGION_ENV
from utils.logging_config import logger as log


class SecretManager:
    def __init__(self):
        self.__github_app_private_key: Optional[str] = None
        self.__github_webhook_secret: Optional[str] = None
        self.__gcp_credentials: Optional[str] = None
        self.__langchain_api_key: Optional[str] = None
        self.__openai_api_key: Optional[str] = None
        self.__client: Any = None

        self.__secrets_cache: Optional[Dict[str, str]] = None

    def init_secrets(self):
        try:
            self.__init_client()
        except Exception as e:
            if os.getenv(ENVIRONMENT_ENV) == "local":
                log.warning(f"Secrets Manager client cannot be initialized: {e}. Running in local environment.")
            else:
                raise ValueError(f"Error while initializing Secrets Manager client: {e}")

        try:
            # self.__init_gcp_credentials() TODO: Uncomment this line if you want to use VertexAI
            self.__init_az_openai_api_key()
            self.__init_github_app_private_key()
            self.__init_github_webhook_secret()
            self.__init_langchain_api_key()
        except Exception as e:
            raise ValueError(f"Error while initializing secrets: {e}")

        try:
            self.__init_gcp_credentials()
        except Exception as e:
            log.warn(f"GCP credentials cannot be initialized: {e}")

    def get_gcp_credentials(self) -> str:
        if not self.__gcp_credentials:
            try:
                self.__init_gcp_credentials()
            except Exception as e:
                raise ValueError(f"Error while initializing GCP credentials: {e}")

        return self.__gcp_credentials

    def get_langchain_api_key(self) -> str:
        if os.getenv(ENVIRONMENT_ENV) == "local":
            return ""

        if not self.__langchain_api_key:
            try:
                self.__init_langchain_api_key()
            except Exception as e:
                raise ValueError(f"Error while initializing Langchain API key: {e}")

        return self.__langchain_api_key

    def get_github_app_private_key(self) -> str:
        if not self.__github_app_private_key:
            try:
                self.__init_github_app_private_key()
            except Exception as e:
                raise ValueError(f"Error while initializing GitHub App private key: {e}")

        return self.__github_app_private_key

    def get_github_webhook_secret(self) -> str:
        if not self.__github_webhook_secret:
            try:
                self.__init_github_webhook_secret()
            except Exception as e:
                raise ValueError(f"Error while initializing GitHub webhook secret: {e}")

        return self.__github_webhook_secret

    def get_azure_openai_api_key(self) -> str:
        if not self.__openai_api_key:
            try:
                self.__init_az_openai_api_key()
            except Exception as e:
                raise ValueError(f"Error while initializing Azure OpenAI API key: {e}")

        return self.__openai_api_key

    def __init_gcp_credentials(self):
        log.debug("Initializing GCP service account secret...")
        service_acc_file_path = os.getenv(GCP_SERVICE_ACCOUNT_FILE_PATH_ENV)
        if service_acc_file_path and os.path.isfile(service_acc_file_path):
            log.debug("Local GCP service account file exists, using that...")
            with open(service_acc_file_path) as f:
                service_acc: str = f.read()
            self.__gcp_credentials = service_acc
            return

        log.debug("Fetching GCP service account from Secrets Manager...")
        try:
            self.__gcp_credentials = self.__fetch_gcp_secret()
        except Exception as e:
            raise ValueError(f"Error while fetching GCP service account from Secrets Manager: {e}")

    def __init_langchain_api_key(self):
        if os.getenv(ENVIRONMENT_ENV) == "local":
            return

        log.debug("Initializing Langchain API key secret...")
        api_key = os.getenv(LANGCHAIN_API_KEY_ENV)
        if api_key:
            log.debug("Langchain API key found in environment variables. Using that...")
            self.__langchain_api_key = api_key
            return

        log.debug("Fetching Langchain API key from Secrets Manager...")
        try:
            self.__langchain_api_key = self.__fetch_langchain_api_key()
        except Exception as e:
            raise ValueError(f"Error while fetching Langchain API key from Secrets Manager: {e}")

    def __init_github_app_private_key(self):
        log.debug("Initializing GitHub App private key secret...")
        file_path = os.getenv(GITHUB_APP_PRIVATE_KEY_FILE_PATH_ENV)
        if file_path and os.path.isfile(file_path):
            log.debug("Github App private key file exists, using that...")
            with open(file_path) as f:
                self.__github_app_private_key = f.read()
            return

        private_key = os.getenv(GITHUB_APP_PRIVATE_KEY_ENV)
        if private_key:
            log.debug("Github App private key found in environment variables. Using that...")
            self.__github_app_private_key = private_key
            return

        log.debug("Fetching GitHub App private key from Secrets Manager...")
        try:
            self.__github_app_private_key = self.__fetch_github_app_private_key()
        except Exception as e:
            raise ValueError(f"Error while fetching GitHub App private key from Secrets Manager: {e}")

    def __init_github_webhook_secret(self):
        log.debug("Initializing GitHub webhook secret...")
        secret = os.getenv("GITHUB_WEBHOOK_SECRET")
        if secret:
            log.debug("GitHub webhook secret found in environment variables. Using that...")
            self.__github_webhook_secret = secret
            return

        log.debug("Fetching GitHub webhook secret from Secrets Manager...")
        try:
            self.__github_webhook_secret = self.__fetch_github_webhook_secret()
        except Exception as e:
            raise ValueError(f"Error while fetching GitHub webhook secret from Secrets Manager: {e}")

    def __init_az_openai_api_key(self):
        log.debug("Initializing OpenAI API key secret...")
        secret = os.getenv(AZURE_OPENAI_API_KEY_ENV)
        if secret:
            log.debug("Aure OpenAI API key found in environment variables. Using that...")
            self.__openai_api_key = secret
            return

        log.debug("Fetching Azure OpenAI API key from Secrets Manager...")
        try:
            self.__openai_api_key = self.__fetch_az_openai_api_key()
        except Exception as e:
            raise ValueError(f"Error while fetching Azure OpenAI API key from Secrets Manager: {e}")

    def __fetch_gcp_secret(self) -> str:
        secret_name = os.getenv("GCP_SERVICE_ACCOUNT_SECRET_NAME")
        if not secret_name:
            raise EnvironmentError("Missing required environment variables for GCP service account secret.")

        log.debug("Pulling GCP service account secret from AWS Secrets Manager...")
        if not self.__client:
            raise ValueError("Client not initialized")
        get_secret_value_response: GetSecretValueResponseTypeDef = self.__client.get_secret_value(SecretId=secret_name)

        secret: str = get_secret_value_response.get("SecretString")
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

    def __fetch_langchain_api_key(self) -> str:
        secrets = self.__fetch_secrets()
        api_key = secrets.get("langchain_api_key")
        if not api_key:
            raise ValueError("API key not found in secrets")
        return api_key

    def __fetch_github_app_private_key(self):
        secrets = self.__fetch_secrets()
        private_key = secrets.get("github_app_private_key")
        if not private_key:
            raise ValueError("GitHub App private key not found in secrets")
        return private_key

    def __fetch_github_webhook_secret(self):
        secrets = self.__fetch_secrets()
        secret = secrets.get("github_webhook_secret")
        if not secret:
            raise ValueError("GitHub webhook secret not found in secrets")
        return secret

    def __fetch_az_openai_api_key(self):
        secrets = self.__fetch_secrets()
        secret = secrets.get("azure_openai_api_key")
        if not secret:
            raise ValueError("Azure OpenAI API key not found in secrets")
        return secret

    @staticmethod
    def __init_client() -> BaseClient:
        region = os.getenv(AWS_SECRET_REGION_ENV)
        if not region:
            raise EnvironmentError("Missing required environment variables for secrets.")
        return boto3.client(service_name="secretsmanager", region_name=region)

secret_manager = SecretManager()