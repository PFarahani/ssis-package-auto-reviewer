import os
import sys
import yaml
import re
from pathlib import Path
from typing import Dict
from config.constants import (
    SQL_SECTION_DELIMITER,
    SQL_USE_STATEMENT,
    SQL_SECTION_HEADER,
    RULES_FILE,
    DEFAULT_PROPERTY_RULES,
    DEFAULT_YAML_COMMENTS
)

def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_property_rules(yaml_file: Path = RULES_FILE) -> Dict:
    """Load and validate property rules from YAML file."""
    with open(yaml_file, 'r') as f:
        rules = yaml.safe_load(f)
    
    validated_rules = {}
    for component, props in rules.items():
        validated_rules[component] = {}
        for prop, config in props.items():
            condition = config['condition']
            value = config.get('value')
            validated_rules[component][prop] = (condition, value)
    
    return validated_rules

def ensure_config_exists(yaml_file: Path = RULES_FILE) -> None:
    """Create default YAML config if it doesn't exist."""
    if not yaml_file.exists():
        yaml_file.parent.mkdir(parents=True, exist_ok=True)
        with open(yaml_file, 'w') as f:
            f.write(DEFAULT_YAML_COMMENTS)
            yaml.safe_dump(DEFAULT_PROPERTY_RULES, f)

def read_sql_file(file_path: Path) -> str:
    """Read and return SQL file content with proper encoding."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def extract_sql_sections(content: str) -> Dict[str, str]:
    """Extract SQL sections from file content."""
    sections = re.split(SQL_SECTION_DELIMITER, content)
    result = {}
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        header_match = re.search(SQL_SECTION_HEADER, section)
        if header_match:
            section_name = header_match.group(1).strip()
            query = section[len(header_match.group(0)):].strip()

            # Remove the USE statements
            query_cleaned = re.sub(SQL_USE_STATEMENT, '', query, flags=re.MULTILINE)
            result[section_name] = query_cleaned.strip()
    
    return result