import os
import logging
from dotenv import load_dotenv

def setup_environment(
    env_file: str = 'db_credentials.env',
    required_vars: list = None,
    template: dict = None,
    logger: logging.Logger = None
) -> bool:
    """
    Initialize and verify environment configuration file.

    Args:
        env_file: Path to the .env file
        required_vars: List of required variable names
        template: Dictionary of default key-value pairs
        logger: Configured logger instance (will create basic one if None)

    Returns:
        True if environment is properly configured, False otherwise

    Raises:
        RuntimeError: If critical configuration is missing
    """

    # Set defaults if not provided
    if logger is None:
        logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    if required_vars is None:
        required_vars = ['SQL_SERVER', 'SQL_DATABASE']

    if template is None:
        template = {
            '#': 'Database credentials',
            'SQL_SERVER': '',
            'SQL_PORT': '1433',
            'SQL_DATABASE': '',
            'SQL_USERNAME': '',
            'SQL_PASSWORD': ''
        }

    file_created = False
    try:
        # Create env file if missing
        if not os.path.exists(env_file):
            try:
                logger.info(f"Creating new environment file: {env_file}")
                with open(env_file, 'w') as f:
                    for key, value in template.items():
                        if key.startswith('#'):
                            f.write(f"# {value}\n")
                        else:
                            f.write(f"{key}={value}\n")
                file_created = True
                logger.warning(
                    f"Created new configuration file at {os.path.abspath(env_file)}\n"
                    "PLEASE EDIT THIS FILE TO ADD YOUR DATABASE CREDENTIALS BEFORE CONTINUING"
                )
                return False
            except IOError as e:
                logger.error(f"Failed to create {env_file}: {str(e)}")
                return False

        # Load and verify environment
        if not load_dotenv(env_file):
            logger.error(f"Failed to load {env_file} - file may be corrupted")
            return False

        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            logger.error(f"Missing required variables: {', '.join(missing)}")
            if file_created:
                logger.error("Template was just created. Fill missing values before restarting.")
            return False

        logger.debug(f"Environment configured from {env_file}")
        return True

    except Exception as e:
        logger.exception(f"Environment setup failed: {str(e)}")
        raise RuntimeError(f"Environment configuration error: {str(e)}")
