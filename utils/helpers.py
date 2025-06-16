import os
import re
import logging
from typing import Pattern, List
import sqlparse
from dotenv import load_dotenv
from config.constants import (
    FRAMEWORK_CONTAINERS,
    COMPONENT_PATTERNS
)


def validate_pattern(input_str: str, patterns: List[Pattern], logger: logging.Logger) -> bool:
    """Validate string against list of regex patterns."""
    for pattern in patterns:
        if pattern.match(input_str):
            logger.debug(f"Valid pattern match: {input_str}")
            return True
    logger.warning(f"Pattern validation failed for: {input_str}")
    return False


def clean_text(text: str) -> str:
    """Normalize and clean text for comparison."""
    return re.sub(r'(\s+|;|\bgo\b)', '', text.strip(), flags=re.IGNORECASE)


def compare_texts(text1: str, text2: str) -> float:
    """Calculate similarity percentage between two cleaned texts."""
    cleaned1 = clean_text(text1)
    cleaned2 = clean_text(text2)

    if not cleaned1 and not cleaned2:
        return 100.0

    max_len = max(len(cleaned1), len(cleaned2))
    matches = sum(1 for a, b in zip(cleaned1, cleaned2) if a == b)
    return round((matches / max_len) * 100, 2)


def validate_component_name(name: str, component_type: str, logger: logging.Logger) -> bool:
    """Validate component name against predefined patterns."""
    pattern = COMPONENT_PATTERNS.get(component_type)
    if not pattern:
        logger.error(f"Invalid component type: {component_type}")
        return False
    return bool(pattern.match(name))


def get_xpath(element, xpath: str, namespaces: dict):
    """Safe XPath value extraction with error handling."""
    result = element.xpath(xpath, namespaces=namespaces)
    return result[0] if result else None


def validate_container_structure(containers: List[str], logger: logging.Logger) -> bool:
    """Validate container names against framework requirements."""
    missing = []
    for pattern in FRAMEWORK_CONTAINERS:
        if not any(p.match(c) for c in containers for p in FRAMEWORK_CONTAINERS):
            missing.append(pattern.pattern)

    if missing:
        logger.warning(f"Missing containers matching patterns: {missing}")
        return False
    return True


def detect_package_type(package_name: str, logger: logging.Logger) -> str:
    """Detect if package is DIM or FACT based on naming convention."""
    if package_name.startswith('Fill_Dim'):
        logger.info("Detected DIMENSION package type")
        return 'DIM'
    elif package_name.startswith('Fill_Fact'):
        logger.info("Detected FACT package type")
        return 'FACT'
    else:
        logger.error("Invalid package naming convention")
        raise ValueError(
            "Package name must start with 'Fill_Dim' or 'Fill_Fact'")


def beautify_sql_query(
    sql_query: str,
    reindent: bool = False,
    reindent_aligned: bool = False,
    keyword_case: str = 'upper',
    strip_comments: bool = False,
    indent_columns: bool = True
) -> str:
    """Beautifies a SQL query by formatting it for improved readability"""
    if not isinstance(sql_query, str) or not sql_query.strip():
        raise ValueError("The SQL query must be a non-empty string.")

    try:
        beautified_query = sqlparse.format(
            sql_query,
            reindent=reindent,
            reindent_aligned=reindent_aligned,
            keyword_case=keyword_case,
            strip_comments=strip_comments,
            indent_columns=indent_columns,
        )
        return beautified_query
    except Exception as e:
        raise RuntimeError(
            f"An error occurred while formatting the SQL query: {e}")


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

    try:
        # Create env file if missing
        if not os.path.exists(env_file):
            logger.info(f"Creating new environment file: {env_file}")
            with open(env_file, 'w') as f:
                for key, value in template.items():
                    if key.startswith('#'):
                        f.write(f"{value}\n")
                    else:
                        f.write(f"{key}={value}\n")
            logger.warning(f"Please configure {env_file} before continuing")
            return False

        # Load and verify environment
        if not load_dotenv(env_file):
            logger.error(f"Failed to load {env_file}")
            return False

        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            logger.error(f"Missing required variables: {', '.join(missing)}")
            return False

        logger.debug(f"Environment configured from {env_file}")
        return True

    except Exception as e:
        logger.exception(f"Environment setup failed: {str(e)}")
        raise RuntimeError(f"Environment configuration error: {str(e)}")
