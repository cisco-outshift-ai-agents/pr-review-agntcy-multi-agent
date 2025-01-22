import base64
import binascii
import json
import os
from typing import Optional, Dict, Any, Literal, List

import boto3
from mypy_boto3_secretsmanager.type_defs import GetSecretValueResponseTypeDef

from utils.constants import ENVIRONMENT_ENV, GCP_SERVICE_ACCOUNT_FILE_PATH_ENV, LANGCHAIN_API_KEY_ENV, \
    GITHUB_APP_PRIVATE_KEY_FILE_PATH_ENV, GITHUB_APP_PRIVATE_KEY_ENV, AZURE_OPENAI_API_KEY_ENV, AWS_SECRET_REGION_ENV, \
    GITHUB_WEBHOOK_SECRET_ENV, AWS_SECRET_NAME_ENV, AWS_GCP_SA_SECRET_NAME_ENV
from utils.logging_config import logger as log


class SecretManager:

    def __init__(self, mandatory_secrets: Optional[
        List[Literal["gcp_credentials", "azure_openai_api_key", "langchain_api_key"]]] = None):
        if mandatory_secrets is None:
            mandatory_secrets = []
        mandatory_secrets.extend(["github_app_private_key", "github_webhook_secret"])

        self.__mandatory_secrets = mandatory_secrets

        self.__github_app_private_key: str
        self.__github_webhook_secret: str
        self.__gcp_credentials: Optional[str] = None
        self.__langchain_api_key: Optional[str] = None
        self.__azure_openai_api_key: Optional[str] = None

        self.__client: Any = None

        self.__secrets_cache_str: Dict[str, str] = {}
        self.__secrets_cache_obj: Dict[str, Dict[str, str]] = {}

        self.__aws_secret_name_cache: Dict[str, str] = {}

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
            self.__init_gcp_credentials()
            self.__init_azure_openai_api_key()
            self.__init_github_app_private_key()
            self.__init_github_webhook_secret()
            self.__init_langchain_api_key()
        except Exception as e:
            raise ValueError(f"Error while initializing secrets: {e}") from e

    def __init_gcp_credentials(self):
        try:
            self.__gcp_credentials = self.__get_secret(
                secret_name="gcp_credentials",
                file_path_env_var=GCP_SERVICE_ACCOUNT_FILE_PATH_ENV,
                env_var=None,
                sm_secret_name=self.__get_gcp_secret_name(),
                sm_secret_field=None)
        except Exception:
            raise

    def __init_langchain_api_key(self):
        if os.getenv(ENVIRONMENT_ENV) == "local":
            return

        try:
            self.__langchain_api_key = self.__get_secret(
                secret_name="langchain_api_key",
                file_path_env_var=None,
                env_var=LANGCHAIN_API_KEY_ENV,
                sm_secret_name=self.__get_general_secret_name(),
                sm_secret_field="langchain_api_key")
        except Exception:
            raise

    def __init_github_app_private_key(self):
        try:
            self.__github_app_private_key = self.__get_secret(
                secret_name="github_app_private_key",
                file_path_env_var=GITHUB_APP_PRIVATE_KEY_FILE_PATH_ENV,
                env_var=GITHUB_APP_PRIVATE_KEY_ENV,
                sm_secret_name=self.__get_general_secret_name(),
                sm_secret_field="github_app_private_key",
                encoding="base64")
        except Exception:
            raise

    def __init_github_webhook_secret(self):
        try:
            self.__github_webhook_secret = self.__get_secret(
                secret_name="github_webhook_secret",
                file_path_env_var=None,
                env_var=GITHUB_WEBHOOK_SECRET_ENV,
                sm_secret_name=self.__get_general_secret_name(),
                sm_secret_field="github_webhook_secret")
        except Exception:
            raise

    def __init_azure_openai_api_key(self):
        try:
            self.__azure_openai_api_key = self.__get_secret(
                secret_name="azure_openai_api_key",
                file_path_env_var=None,
                env_var=AZURE_OPENAI_API_KEY_ENV,
                sm_secret_name=self.__get_general_secret_name(),
                sm_secret_field="azure_openai_api_key")
        except Exception:
            raise

    def __get_secret(self, secret_name: str, env_var: Optional[str], file_path_env_var: Optional[str],
                     sm_secret_name: Optional[str],
                     sm_secret_field: Optional[str], encoding: Optional[Literal["base64"]] = None) -> str:
        log.debug(f"Initializing secret {secret_name}...")
        log.debug("Checking file...")
        if file_path_env_var:
            try:
                secret = self.__get_secret_from_file(file_path_env_var)
                if secret:
                    return secret
            except ValueError as e:
                raise ValueError(f"Error while getting secret from file: {e}") from e

        log.debug("Checking environment variable...")
        if env_var:
            try:
                secret = self.__get_secret_from_env_var(env_var, encoding)
                if secret:
                    return secret
            except ValueError as e:
                raise ValueError(f"Error while getting secret from environment variable: {e}") from e

        log.debug("Checking AWS Secrets Manager...")
        if sm_secret_name:
            try:
                secret = self.__get_secret_from_secret_manager(secret_name, sm_secret_field, encoding)
                if secret:
                    return secret
            except ValueError as e:
                raise ValueError(f"Error while getting secret from Secrets Manager: {e}") from e

        if secret_name in self.__mandatory_secrets:
            raise ValueError(f"Secret {secret_name} cannot be initialized because no source was given")

        return ""

    def __fetch_secret(self, secret_name: str) -> str:
        if not self.__client:
            try:
                self.__init_client()
            except Exception as e:
                raise ValueError(f"Error while initializing AWS Secrets Manager client: {e}") from e

        try:
            get_secret_value_response: GetSecretValueResponseTypeDef = self.__client.get_secret_value(
                SecretId=secret_name)
        except Exception as e:
            raise ValueError(f"Error while fetch secret from AWS SM: {e}") from e

        secret: str = get_secret_value_response.get("SecretString", "")
        if not secret:
            raise ValueError(f"Got invalid secret structure from AWS SM")

        return secret

    def __init_client(self):
        region = os.getenv(AWS_SECRET_REGION_ENV)
        if not region:
            raise EnvironmentError("Missing required environment variables for secrets.")
        self.__client = boto3.client(service_name="secretsmanager", region_name=region)

    # Error is not raised in this function if a secret or a secret field not found
    # because it is the default source of secrets, and it can happen that some
    # secrets are not present in the AWS Secrets Manager, but they are not mandatory
    def __get_secret_from_secret_manager(self, secret_name: str, secret_field: Optional[str],
                                         encoding: Optional[Literal["base64"]] = None) -> str:
        if not self.__secrets_cache_str.get(secret_name, None):
            try:
                self.__secrets_cache_str[secret_name] = self.__fetch_secret(secret_name)
            except Exception as e:
                log.debug(f"Secret named {secret_name} not found in AWS Secrets Manager: {e}")
                return ""

        secret_json: str = self.__secrets_cache_str.get(secret_name, "")

        if not secret_field:
            return secret_json

        if not self.__secrets_cache_obj.get(secret_name, None):
            try:
                self.__secrets_cache_obj[secret_name] = json.loads(secret_json)
            except Exception as e:
                raise ValueError(f"Error while parsing secret {secret_name} to object: {e}") from e

        secret = self.__secrets_cache_obj[secret_name].get(secret_field, "")
        if not secret:
            raise ValueError(f"Secret field {secret_field} not found in secret {secret_name}")

        if encoding and encoding == "base64":
            try:
                secret = self.__decode_base64(secret)
            except binascii.Error as e:
                raise ValueError(f"Error while decoding base64 secret: {e}") from e

        return secret

    def __get_secret_from_env_var(self, env_var: str, encoding: Optional[Literal["base64"]] = None) -> str:
        secret = os.getenv(env_var)
        if not secret:
            return ""

        if encoding and encoding == "base64":
            try:
                return self.__decode_base64(secret)
            except binascii.Error as e:
                raise ValueError(f"Error while decoding base64 secret: {e}") from e

        return secret

    def __get_general_secret_name(self) -> str:
        if not self.__aws_secret_name_cache.get("general", None):
            self.__aws_secret_name_cache["general"] = os.getenv(AWS_SECRET_NAME_ENV)

        return self.__aws_secret_name_cache["general"]

    def __get_gcp_secret_name(self) -> str:
        if not self.__aws_secret_name_cache.get("gcp", None):
            self.__aws_secret_name_cache["gcp"] = os.getenv(AWS_GCP_SA_SECRET_NAME_ENV)

        return self.__aws_secret_name_cache["gcp"]

    @staticmethod
    def __get_secret_from_file(path_env_var: str) -> str:
        file_path = os.getenv(path_env_var)
        if not file_path or not os.path.isfile(file_path):
            return ""

        try:
            with open(file_path) as f:
                secret = f.read()
                return secret
        except OSError as e:
            raise ValueError(f"Error while reading file {file_path}: {e}") from e

    @staticmethod
    def __decode_base64(secret: str) -> str:
        try:
            return base64.b64decode(secret).decode("utf-8")
        except binascii.Error:
            raise


secret_manager: Optional[SecretManager] = None
if os.getenv("TESTENV") != "true":
    secret_manager = SecretManager(mandatory_secrets=["azure_openai_api_key", "langchain_api_key"])
