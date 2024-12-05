import json
import os
from typing import Optional
import boto3
from langchain_openai import AzureChatOpenAI
from langchain_google_vertexai.model_garden import ChatAnthropicVertex
from google.oauth2 import service_account
from utils.logging_config import logger as log
from pydantic import SecretStr


class ChatModelFactory:
    def __init__(self) -> None:
        self.__azure_openai: Optional[AzureChatOpenAI] = None
        self.__vertexai: Optional[ChatAnthropicVertex] = None

    def get_azure_openai(self) -> AzureChatOpenAI:
        if not self.__azure_openai:
            self.__azure_openai = self.__init_azure_openai()
        return self.__azure_openai

    def get_vertexai(self) -> ChatAnthropicVertex:
        if not self.__vertexai:
            self.__vertexai = self.__init_vertexai()
        return self.__vertexai

    def __init_vertexai(self) -> ChatAnthropicVertex:
        log.debug("Initializing ChatAnthropicVertex model...")

        try:
            credentials = self.__get_gcp_credentials()
        except Exception as e:
            log.error(f"Error while getting GCP credentials for VertexAI: {e}")
            raise EnvironmentError(f"Invalid enviroment config for getting GCP credentials: {e}")

        return ChatAnthropicVertex(
            model=os.getenv("VERTEXAI_MODEL"), location=os.getenv("VERTEXAI_GCP_REGION"), credentials=credentials, temperature=0
        )

    def __get_gcp_credentials(self) -> service_account.Credentials:
        service_acc_file_path = os.getenv("GCP_SERVICE_ACCOUNT")
        if service_acc_file_path and os.path.isfile(service_acc_file_path):
            log.debug("Local GCP service account file exists, using that...")
            with open(service_acc_file_path) as f:
                service_acc = f.read()
        else:
            # For Lambda run we need to download the GCP service account file from Secrets Manager
            log.debug("Local GCP service account file doesn't exist, trying to fetch from Secrets Manager...")
            service_acc = self.__get_gcp_service_acc_from_secrets_manager()

        json_acct_info = json.loads(service_acc)
        credentials = service_account.Credentials.from_service_account_info(json_acct_info)

        return credentials.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])

    @staticmethod
    def __get_gcp_service_acc_from_secrets_manager() -> str:
        secret_name = os.getenv("GCP_SERVICE_ACCOUNT_SECRET_NAME")
        region_name = os.getenv("GCP_SERVICE_ACCOUNT_SECRET_REGION")
        if not secret_name or not region_name:
            raise EnvironmentError("Missing required environment variables for GCP service account secret.")

        log.debug("Pulling GCP service account secret...")
        client = boto3.client(service_name="secretsmanager", region_name=region_name)
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)

        secret = get_secret_value_response.get("SecretString")
        if not secret:
            raise ValueError("Got invalid GCP service account credentials from Secrets Manager")
        return secret

    @staticmethod
    def __init_azure_openai() -> AzureChatOpenAI:
        log.debug("Initializing AzureChatOpenAI model...")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        return AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            api_key=SecretStr(api_key) if api_key else None,
        )


# Initialize the factory so other modules can use it
models = ChatModelFactory()
