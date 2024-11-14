from dotenv import load_dotenv


def initialize_environment(local_run):
    env_local_path = ".env"

    # Check if .env file exists
    if not local_run:
        # NOTE: Do we need this brach?
        print(".env file not found. Downloading from somewhere...")
    else:
        # Load the environment variables from the .env file
        load_dotenv(env_local_path)

        print(".env file loaded successfully")
