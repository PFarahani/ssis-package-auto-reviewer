import re
import logging
from typing import Pattern, List
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
        raise ValueError("Package name must start with 'Fill_Dim' or 'Fill_Fact'")