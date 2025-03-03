import asyncio
from datetime import datetime
from io import BytesIO
from typing import List, Optional, cast
from azure.storage.blob.aio import (
    BlobServiceClient as AsyncBlobServiceClient,
    ContainerClient as AsyncContainerClient,
)
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContainerClient
import streamlit as st


from utils.logger import logger
from config import (
    AZURE_STORAGE_CONNECTION_STRING,
    AZURE_STORAGE_CONTAINER_NAME,
    LABELLING_DATETIME_FORMAT,
)


@st.cache_resource(show_spinner=False)
def get_container_client(
    sync: bool = False,
    blob_container_name: str | None = AZURE_STORAGE_CONTAINER_NAME(),
    blob_connection_string: str | None = AZURE_STORAGE_CONNECTION_STRING(),
) -> ContainerClient | AsyncContainerClient | None:
    """
    Retrieves the container client for the specified blob container.
    Args:
        sync (bool, optional): Indicates whether to use synchronous client. Defaults to False and uses asynchronous client.
        blob_container_name (str | None, optional): The name of the blob container. Defaults to AZURE_STORAGE_CONTAINER_NAME().
        blob_connection_string (str | None, optional): The connection string for the blob storage account. Defaults to AZURE_STORAGE_CONNECTION_STRING().
    Returns:
        ContainerClient | AsyncContainerClient | None: The container client if successful, None otherwise.
    """

    if blob_container_name is None or blob_connection_string is None:
        logger.warning("Blob container name or connection string is None.")
        return None

    service_client = BlobServiceClient if sync else AsyncBlobServiceClient
    account_name = blob_connection_string.split(";")[1].split("AccountName=")[1]
    account_url = f"https://{account_name}.blob.core.windows.net"
    credential = DefaultAzureCredential()
    try:
        blob_service_client = service_client(account_url, credential)
        # Check if the access is successful
        blob_service_client.get_service_properties()
    except Exception as e:
        logger.error(
            f"Error getting blob service client via DefaultAzureCredential: {e}"
        )
        try:
            blob_service_client = service_client.from_connection_string(
                blob_connection_string
            )
        except Exception as e:
            logger.error(
                f"Error getting blob service client via connection string: {e}"
            )
            return None

    try:
        return blob_service_client.get_container_client(blob_container_name)
    except Exception as e:
        logger.error(f"Error getting container client: {e}")
        return None


def get_datetime_from_filename(file_name: str) -> Optional[datetime]:
    """
    Extracts datetime from a given file name.
    Args:
        file_name (str): The file name from which to extract the datetime.
    Returns:
        datetime: The extracted datetime from the file name, or None if the file name is invalid.
    """

    if len(file_name.split("/")) > 1:
        file_name = file_name.split("/")[-1]
    else:
        return None
    if len(file_name.split("_")) > 1:
        return datetime.strptime(file_name.split("_")[0], LABELLING_DATETIME_FORMAT)
    return None


def get_file_name_without_datetime(file_name: str) -> Optional[str]:
    """
    Returns the file name without the datetime prefix.
    Args:
        file_name (str): The file name with datetime prefix.
    Returns:
        str: The file name without the datetime prefix, or None if the file name is invalid.
    """

    if len(file_name.split("/")) > 1:
        folder = file_name.split("/")[0]
        _file = file_name.split("/")[-1]
    else:
        return None
    if len(_file.split("_")) > 1:
        return folder + "/" + "_".join(_file.split("_")[1:])
    return None


async def delete_old_entries(file_name: str, container_client: AsyncContainerClient):
    """
    Deletes old entries from the specified file in the Azure Blob container.
    Args:
        file_name (str): The name of the file to delete old entries from.
        container_client (AsyncContainerClient): The client for interacting with the Azure Blob container.
    Returns:
        None: This function does not return anything.
    Raises:
        Exception: If there is an error while deleting old entries.
    """

    current_datetime = get_datetime_from_filename(file_name)
    if current_datetime is None:
        return
    file_name_without_datetime = get_file_name_without_datetime(file_name)
    tasks = []
    logger.info(f"Deleting old entries from {file_name}...")
    try:
        async for file in container_client.list_blobs():
            if get_file_name_without_datetime(file.name) == file_name_without_datetime:
                logger.info(f"File {file.name} is in the same group.")
                file_datetime = get_datetime_from_filename(file.name)
                if file_datetime and file_datetime < current_datetime:
                    logger.info(f"Deleting old entry {file.name}.")
                    tasks.append(container_client.delete_blob(file.name))
        await asyncio.gather(*tasks)
        logger.error(f"Deleted old entries from {file_name}.")
    except Exception as e:
        logger.error(f"Error deleting old entries: {e}")


async def upload_to_blob(
    file_name: str,
    entry: str,
    container_client_: AsyncContainerClient | None = None,
    delete_old_entries: bool = False,
):
    """
    Uploads the given entry to Azure Blob Storage.

    Parameters:
    - file_name (str): The name of the file/blob to upload the entry to.
    - entry (str): The entry to be uploaded.
    - container_client_ (AsyncContainerClient | None): Optional container client. If not provided, a new container client will be created.
    - delete_old_entries (bool): Flag indicating whether to delete old entries in the blob.

    Returns:
        None
    """

    logger.info("Uploading to blob...")
    if container_client_ is None:
        container_client: AsyncContainerClient = cast(
            AsyncContainerClient, get_container_client()
        )
    else:
        container_client = container_client_

    logger.info(f"Uploading entry to {file_name}...")
    try:
        # Upload updated content
        await container_client.upload_blob(file_name, entry, overwrite=True)
        logger.info(f"Uploaded entry to {file_name}.")
        if delete_old_entries:
            await delete_old_entries(
                file_name=file_name, container_client=container_client
            )
    except Exception as e:
        # If blob doesn't exist or there's an error, create new blob with single entry
        logger.warning(f"Error during blob update, attempting to create new: {e}")
        await container_client.upload_blob(file_name, entry)
        if delete_old_entries:
            await delete_old_entries(
                file_name=file_name, container_client=container_client
            )
    finally:
        if container_client is not None and container_client_ is None:
            await container_client.close()


def list_files_in_blob(
    blob_container_name: str | None = AZURE_STORAGE_CONTAINER_NAME(),
    blob_connection_string: str | None = AZURE_STORAGE_CONNECTION_STRING(),
    folder: str = "",
    extension: str = "",
) -> Optional[List[str]]:
    """
    Lists the files in the Azure blob storage container.
    Args:
        blob_container_name (str | None): The name of the blob storage container. Defaults to the value of AZURE_STORAGE_CONTAINER_NAME().
        blob_connection_string (str | None): The connection string for the blob storage account. Defaults to the value of AZURE_STORAGE_CONNECTION_STRING().
        folder (str): The folder path within the container. Defaults to an empty string.
        extension (str): The file extension to filter by. Defaults to an empty string.
    Returns:
        Optional[List[str]]: A list of file names in the specified container and folder. Returns None if the container client is None or an error occurs.
    """
    container_client = cast(
        ContainerClient,
        get_container_client(
            sync=True,
            blob_container_name=blob_container_name,
            blob_connection_string=blob_connection_string,
        ),
    )
    if container_client is None:
        logger.warning("Container client is None.")
        return None
    kwargs = {}
    if folder:
        kwargs["name_starts_with"] = folder
    try:
        file_names = [blob.name for blob in container_client.list_blobs(**kwargs)]
        if extension:
            file_names = [file for file in file_names if file.endswith(extension)]
        if not folder:
            file_names = [file for file in file_names if "/" not in file]
        return file_names
    except Exception as e:
        logger.error(f"Error listing blobs: {e}")
        return []


def download_file_from_blob(
    file_name: str,
    blob_container_name: str | None = AZURE_STORAGE_CONTAINER_NAME(),
    blob_connection_string: str | None = AZURE_STORAGE_CONNECTION_STRING(),
) -> Optional[BytesIO]:
    """
    Downloads a file from an Azure Blob Storage container.
    Args:
        file_name (str): The name of the file to download.
        blob_container_name (str, optional): The name of the Azure Blob Storage container. Defaults to the value of AZURE_STORAGE_CONTAINER_NAME().
        blob_connection_string (str, optional): The connection string for the Azure Blob Storage account. Defaults to the value of AZURE_STORAGE_CONNECTION_STRING().
    Returns:
        Optional[BytesIO]: A BytesIO object containing the downloaded file, or None if an error occurred.
    """
    container_client = cast(
        ContainerClient,
        get_container_client(
            sync=True,
            blob_container_name=blob_container_name,
            blob_connection_string=blob_connection_string,
        ),
    )
    try:
        blob_client = container_client.get_blob_client(file_name)
        file = BytesIO()
        file.write(blob_client.download_blob().readall())
        file.seek(0)
        return file
    except Exception as e:
        logger.error(f"Error downloading blob: {e}")
        return None
