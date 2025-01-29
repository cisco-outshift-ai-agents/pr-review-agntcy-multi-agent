import os
from typing import Optional

from google.oauth2 import service_account
from langchain_google_vertexai.model_garden import ChatAnthropicVertex
from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr

from utils.logging_config import logger as log
from utils.secret_manager import secret_manager


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
            raise EnvironmentError(f"Invalid environment config for getting GCP credentials: {e}") from e

        return ChatAnthropicVertex(
            model=os.getenv("VERTEXAI_MODEL"), location=os.getenv("VERTEXAI_GCP_REGION"), credentials=credentials, temperature=0
        )

    def __get_gcp_credentials(self) -> service_account.Credentials:
        if not secret_manager or secret_manager.gcp_credentials is None:
            raise ValueError("GCP credentials are missing")

        credentials = service_account.Credentials.from_service_account_info(secret_manager.gcp_credentials)
        return credentials.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])

    @staticmethod
    def __init_azure_openai() -> AzureChatOpenAI:
        log.debug("Initializing AzureChatOpenAI model...")
        if not secret_manager or secret_manager.azure_openai_api_key is None:
            raise ValueError("Azure OpenAI API key is missing")

        return AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            api_key=SecretStr(secret_manager.azure_openai_api_key),
            temperature=0,
        )


# Initialize the factory so other modules can use it
models = ChatModelFactory()
