from google.cloud import storage
from dotenv import load_dotenv


def download_file_from_gcs(bucket_name, gcs_blob_name, local_path):
    # Create a storage client
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(gcs_blob_name)

    # Download the file from GCS
    blob.download_to_filename(local_path)
    print(f"File {local_path} successfully downloaded from GCS")


def initialize_environment(local_run):
    bucket_name = "pr-coach"
    env_file_in_gcs = "env"
    private_key_in_gcs = "private-key.pem"
    tmp_for_gcs = "/tmp/"
    env_local_path = ".env"
    private_key_local_path = "private-key.pem"

    # Check if .env file exists
    if not local_run:
        print(".env file not found. Downloading from GCS...")
        download_file_from_gcs(bucket_name, env_file_in_gcs, tmp_for_gcs + env_local_path)
        download_file_from_gcs(bucket_name, private_key_in_gcs, tmp_for_gcs + private_key_local_path)
        load_dotenv(tmp_for_gcs + env_local_path)
    else:
        # Load the environment variables from the .env file
        load_dotenv(env_local_path)

    print(".env file loaded successfully")
