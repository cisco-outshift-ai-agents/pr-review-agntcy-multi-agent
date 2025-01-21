import base64
import json
import os
from typing import Dict, List, Literal, Optional
from unittest.mock import patch

import pytest

from utils.secret_manager import SecretManager


class TestSecretManager:

    @pytest.fixture()
    def set_secret_file(self, tmp_path):
        path = tmp_path / "secret.pem"

        def create_secret_file(secret_value: str):
            with open(path, "w") as f:
                f.write(secret_value)
            return path

        yield create_secret_file
        if os.path.isfile(path):
            os.remove(path)

    @pytest.fixture()
    def mock_client(self):
        patchers = []

        def wrapper(throw_sm_exception=False, secret_name: Literal["gcp", "base"] = "base"):
            class Client:
                @staticmethod
                def get_secret_value(SecretId: str):
                    if throw_sm_exception:
                        raise Exception("AWS Secrets Manager exception")

                    secrets = json.dumps({
                        "github_app_private_key": base64.b64encode(b"sm_github_app_private_key").decode("utf-8"),
                        "github_webhook_secret": "sm_github_webhook_secret",
                        "langchain_api_key": "sm_langchain_api_key",
                        "azure_openai_api_key": "sm_azure_openai_api_key",
                    })

                    return {"SecretString": secrets if secret_name == "base" else "sm_gcp_credentials"}

            boto_patcher = patch("boto3.client", return_value=Client())
            env_patcher = patch.dict("os.environ", {"AWS_SECRET_REGION": "eu-central-1"})
            patchers.append(boto_patcher)
            patchers.append(env_patcher)
            boto_patcher.start()
            env_patcher.start()

        yield wrapper
        for p in patchers:
            p.stop()

    @pytest.fixture()
    def mock_inits(self):
        patchers = []

        def mock(inits: List[
            Literal[
                "gcp_credentials", "github_app_private_key", "github_webhook_secret", "azure_openai_api_key", "langchain_api_key"]]):
            for init in inits:
                patcher = patch.object(SecretManager, f"_SecretManager__init_{init}", return_value=None)
                patchers.append(patcher)
                patcher.start()

        yield mock
        for p in patchers:
            p.stop()

    @pytest.fixture()
    def env_vars(self, tmp_path, request):
        envs: Dict[str, str] = request.param
        if not envs:
            envs = {}
        envs["AWS_SECRET_NAME"] = "aws_secret_name"
        for key, value in envs.items():
            if key.endswith("_FILE"):
                envs[key] = str(tmp_path / value)
        with patch.dict("os.environ", envs, clear=True):
            yield envs

    @pytest.mark.parametrize(
        ["env_vars", "secret_in_file", "is_aws_sm_error", "expected_secret", "expected_error_type"],
        [
            (
                    # file set, env set, should use file,
                    {"GITHUB_APP_PRIVATE_KEY_FILE": "secret.pem", "GITHUB_APP_PRIVATE_KEY": "secret_in_env"},
                    "secret_in_file",
                    False,
                    "secret_in_file",
                    None,
            ),
            (
                    # file not set, env set, should use env,
                    {"GITHUB_APP_PRIVATE_KEY": base64.b64encode(b"secret_in_env").decode("utf-8")},
                    "secret_in_file",
                    False,
                    "secret_in_env",
                    None,
            ),
            (
                    # file not set, env not set, should use aws secret,
                    None,
                    "secret_in_file",
                    False,
                    "sm_github_app_private_key",
                    None
            ),
            (
                    # file not set, env not set, aws sm error, should raise exception,
                    None,
                    "secret_in_file",
                    True,
                    "",
                    ValueError
            )
        ],
        indirect=["env_vars"],
    )
    def test_github_app_private_key(self,
                                    set_secret_file,
                                    mock_inits,
                                    mock_client,
                                    tmp_path,
                                    env_vars: Dict[str, str],
                                    secret_in_file: str,
                                    is_aws_sm_error: bool,
                                    expected_secret: str,
                                    expected_error_type: Optional[type]
                                    ):
        with patch.dict("os.environ", env_vars):
            # Arrange
            mock_inits(["gcp_credentials", "github_webhook_secret", "azure_openai_api_key", "langchain_api_key"])
            mock_client(throw_sm_exception=is_aws_sm_error)

            if secret_in_file:
                set_secret_file(secret_in_file)

            if expected_error_type:
                # Act
                with pytest.raises(Exception) as e_info:
                    SecretManager()
                # Assert
                assert isinstance(e_info.value, expected_error_type)

            else:
                # Act
                sm = SecretManager()
                # Assert
                assert sm.github_app_private_key == expected_secret

    @pytest.mark.parametrize(
        ["env_vars", "is_aws_sm_error", "expected_secret", "expected_error_type"],
        [
            (
                    # env set, should use env,
                    {"GITHUB_WEBHOOK_SECRET": "secret_in_env"},
                    False,
                    "secret_in_env",
                    None,
            ),
            (
                    # env not set, should use aws secret,
                    None,
                    False,
                    "sm_github_webhook_secret",
                    None
            ),
            (
                    # env not set, aws sm error, should raise exception,
                    None,
                    True,
                    "",
                    ValueError
            )
        ],
        indirect=["env_vars"])
    def test_github_webhook_secret(self,
                                   mock_inits,
                                   mock_client,
                                   env_vars: Dict[str, str],
                                   is_aws_sm_error: bool,
                                   expected_secret: str,
                                   expected_error_type: Optional[type]
                                   ):
        # Arrange
        mock_inits(["gcp_credentials", "github_app_private_key", "azure_openai_api_key", "langchain_api_key"])
        mock_client(throw_sm_exception=is_aws_sm_error)

        if expected_error_type:
            # Act
            with pytest.raises(Exception) as e_info:
                SecretManager()
            # Assert
            assert isinstance(e_info.value, expected_error_type)

        else:
            # Act
            sm = SecretManager()
            # Assert
            assert sm.github_webhook_secret == expected_secret

    @pytest.mark.parametrize(
        ["env_vars", "is_aws_sm_error", "mandatory_secrets", "expected_secret", "expected_error_type"],
        [
            (
                    # env set, should use env,
                    {"LANGCHAIN_API_KEY": "secret_in_env"},
                    False,
                    ["langchain"],
                    "secret_in_env",
                    None,
            ),
            (
                    # env not set, should use aws secret,
                    None,
                    False,
                    ["langchain"],
                    "sm_langchain_api_key",
                    None
            ),
            (
                    # env not set, aws sm error, key not mandatory,
                    None,
                    True,
                    [],
                    None,
                    None
            ),
            (
                    # env not set, aws sm error, should raise exception,
                    None,
                    True,
                    ["langchain"],
                    "",
                    ValueError
            ),
        ],
        indirect=["env_vars"])
    def test_langchain_api_key(self,
                               mock_inits,
                               mock_client,
                               env_vars: Dict[str, str],
                               is_aws_sm_error: bool,
                               mandatory_secrets: List[Literal["langchain"]],
                               expected_secret: str,
                               expected_error_type: Optional[type]
                               ):
        # Arrange
        mock_inits(["gcp_credentials", "github_app_private_key", "github_webhook_secret", "azure_openai_api_key"])
        mock_client(throw_sm_exception=is_aws_sm_error)

        if expected_error_type:
            # Act
            with pytest.raises(Exception) as e_info:
                SecretManager(mandatory_secrets=mandatory_secrets)
            # Assert
            assert isinstance(e_info.value, expected_error_type)

        else:
            # Act
            sm = SecretManager(mandatory_secrets=mandatory_secrets)
            # Assert
            assert sm.langchain_api_key == expected_secret

    @pytest.mark.parametrize(
        ["env_vars", "is_aws_sm_error", "mandatory_secrets", "expected_secret", "expected_error_type"],
        [
            (
                    # env set, should use env,
                    {"AZURE_OPENAI_API_KEY": "secret_in_env"},
                    False,
                    ["openai"],
                    "secret_in_env",
                    None,
            ),
            (
                    # env not set, should use aws secret,
                    None,
                    False,
                    ["openai"],
                    "sm_azure_openai_api_key",
                    None
            ),
            (
                    # env not set, aws sm error, key not mandatory,
                    None,
                    True,
                    [],
                    None,
                    None
            ),
            (
                    # env not set, aws sm error, should raise exception,
                    None,
                    True,
                    ["openai"],
                    "",
                    ValueError
            ),
        ],
        indirect=["env_vars"])
    def test_azure_openai_api_key(self,
                                  mock_inits,
                                  mock_client,
                                  env_vars: Dict[str, str],
                                  is_aws_sm_error: bool,
                                  mandatory_secrets: List[Literal["openai"]],
                                  expected_secret: str,
                                  expected_error_type: Optional[type]
                                  ):
        # Arrange
        mock_inits(["gcp_credentials", "github_app_private_key", "github_webhook_secret", "langchain_api_key"])
        mock_client(throw_sm_exception=is_aws_sm_error)

        if expected_error_type:
            # Act
            with pytest.raises(Exception) as e_info:
                SecretManager(mandatory_secrets=mandatory_secrets)
            # Assert
            assert isinstance(e_info.value, expected_error_type)

        else:
            # Act
            sm = SecretManager(mandatory_secrets)
            # Assert
            assert sm.azure_openai_api_key == expected_secret

    @pytest.mark.parametrize(
        ["env_vars", "mandatory_secrets", "secret_in_file", "is_aws_sm_error", "expected_secret",
         "expected_error_type"],
        [
            # (
            #         # aws sm error, should raise exception,
            #         {"GCP_SERVICE_ACCOUNT_FILE": "secret.pem", "AWS_GCP_SA_SECRET_NAME": "aws_secret_name"},
            #         ["gcp"],
            #         "secret_in_file",
            #         False,
            #         "secret_in_file",
            #         None
            # ),
            (
                    # aws sm error, should raise exception,
                    {"AWS_GCP_SA_SECRET_NAME": "aws_secret_name"},
                    ["gcp"],
                    "secret_in_file",
                    False,
                    "sm_gcp_credentials",
                    None
            ),
            (
                    # aws sm error, key not mandatory,
                    {"AWS_GCP_SA_SECRET_NAME": "aws_secret_name"},
                    [],
                    "secret_in_file",
                    True,
                    None,
                    None
            ),
            (
                    # aws sm error, key mandatory,
                    {"AWS_GCP_SA_SECRET_NAME": "aws_secret_name"},
                    ["gcp"],
                    "secret_in_file",
                    True,
                    None,
                    ValueError
            )
        ],
        indirect=["env_vars"])
    def test_gcp_credentials(self,
                             mock_inits,
                             mock_client,
                             set_secret_file,
                             env_vars: Dict[str, str],
                             mandatory_secrets: List[Literal["gcp"]],
                             secret_in_file,
                             is_aws_sm_error: bool,
                             expected_secret: str,
                             expected_error_type: Optional[type]
                             ):
        # Arrange
        mock_inits(["github_app_private_key", "github_webhook_secret", "azure_openai_api_key", "langchain_api_key"])
        mock_client(throw_sm_exception=is_aws_sm_error, secret_name="gcp")
        if secret_in_file:
            set_secret_file(secret_in_file)

        if expected_error_type:
            # Act
            with pytest.raises(Exception) as e_info:
                SecretManager(mandatory_secrets)
            # Assert
            assert isinstance(e_info.value, expected_error_type)

        else:
            # Act
            sm = SecretManager(mandatory_secrets)
            # Assert
            assert sm.gcp_credentials == expected_secret
