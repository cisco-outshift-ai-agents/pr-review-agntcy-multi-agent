import base64
import os
import requests
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv


class AzureClient:
  def __init__(self):
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    url = os.getenv("AZURE_OPENAI_AUTH_URL")
    payload = "grant_type=client_credentials"
    value = base64.b64encode(f'{client_id}:{client_secret}'.encode('utf-8')).decode('utf-8')
    headers = {
      "Accept": "*/*",
      "Content-Type": "application/x-www-form-urlencoded",
      "Authorization": f"Basic {value}"
    }
    self.token_response = requests.request("POST", url, headers=headers, data=payload)

  def get_azure_client(self) -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=self.token_response.json()["access_token"],
        api_version="2023-08-01-preview",
        model="gpt-4o-mini",
        user=f'{{"appkey": "{os.getenv("AZURE_OPENAI_APP_KEY")}"}}',
        temperature=0,
    )