import os

from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError
from dotenv import load_dotenv

from utils.logger import logger

load_dotenv()

# ----------------------------------------------------------------------------------------------------
# AZURE KEY VAULT ENVIRONMENT VARIABLES
# ----------------------------------------------------------------------------------------------------

# Cannot declare this variable in config.py - circular import
AZURE_KEY_VAULT_ENDPOINT = lambda: os.environ.get("AZURE_KEY_VAULT_ENDPOINT")


class SecretManager:
    """
    A class for managing secrets.

    This class provides methods to retrieve secrets from Azure Key Vault or environment variables.
    """

    def __init__(self):
        self.secret_client = None
        key_vault_url = AZURE_KEY_VAULT_ENDPOINT()
        if key_vault_url:
            try:
                credential = DefaultAzureCredential(
                    exclude_shared_token_cache_credential=True
                )
                self.secret_client = SecretClient(
                    vault_url=key_vault_url, credential=credential
                )
            except Exception as e:
                logger.error(f"Error getting secret client: {e}")

        self.do_not_use_key_vault = False

    def get_secret(self, key: str, default_value=None) -> str | None:
        """
        Get the value of a secret.

        This method retrieves the value of a secret with the given key. If the secret is stored in Azure Key Vault,
        it will be fetched from there. Otherwise, it will be fetched from environment variables.

        Args:
            key (str): The key of the secret.
            default_value: The default value to return if the secret is not found.

        Returns:
            str: The value of the secret, or the default value if the secret is not found.
        """
        logger.debug(f"Getting secret {key}")
        if self.secret_client is not None and not self.do_not_use_key_vault:
            try:
                val = self.secret_client.get_secret(key.replace("_", "-")).value
                logger.info(f"Got secret {key}")
                return val
            except ResourceNotFoundError:
                logger.warning(f"Secret {key} not found in key vault.")
            except Exception as e:
                logger.error(f"Error getting secret {key}: {e}")
                self.do_not_use_key_vault = True

        logger.debug(f"Getting secret {key} from environment variables")
        return os.environ.get(key, default_value)


secret_manager = SecretManager()
