from pathlib import Path
import re
import sys
from os import getenv

class _DatabaseConfig:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._database = None
            self._database_stage = None
            self._initialized = True

    @property
    def DATABASE(self):
        if self._database is None:
            self._load_env_vars()
        return self._database

    @property
    def DATABASE_STAGE(self):
        if self._database_stage is None:
            self._load_env_vars()
        return self._database_stage

    @property
    def QUERY_DB_MAP(self):
        """Lazily evaluated mapping that uses current DB values"""
        if not self._initialized:
            raise RuntimeError("Database config not initialized")
        
        # TODO:
        # - Remove the DB Mapping since it is already being handled by connection lookup 
        
        return {
            re.compile(r"^\bGet\s+Last\s+Value\s+for\s+\w+\b$", re.IGNORECASE): self._database,
            re.compile(r"^\bCreate\s+Table\s+(?:Dim|Fact)\w*Stage\b$", re.IGNORECASE): self._database_stage,
            re.compile(r"^\bGet\s+(?:Record|Data)\s+from\s+(?!\w*Stage\b)(\w+)\b$", re.IGNORECASE): None,
            re.compile(r"^V_FullLoadQuery(?:_\w+|\w*)$", re.IGNORECASE): None,
            re.compile(r"^V_IncrementalLoadQuery(?:_\w+|\w*)$", re.IGNORECASE): None,
            re.compile(r"^V_Query(?:_\w+|\w*)$", re.IGNORECASE): None,
            re.compile(r"^\bCreate\s+Clustered\s+Index\s+on\s+(?:Dim|Fact)\w*Stage\b$", re.IGNORECASE): self._database_stage,
            re.compile(r"^\bUpdate\s+IsExists\b$", re.IGNORECASE): self._database_stage,
            re.compile(r"^\bGet\s+(?:Record|Data)\s+from\s+(?:Dim|Fact)\w*Stage\b$", re.IGNORECASE): self._database_stage,
            re.compile(r"^\bUpdate\s+(?:Dim|Fact)(?!\w*Stage\b)(\w+)\b$", re.IGNORECASE): self._database,
            re.compile(r"^\bUpdate\s+ConfigTable\b$", re.IGNORECASE): self._database,
            re.compile(r"^\bInsert\s+PackageLog\b$", re.IGNORECASE): self._database,
            }

    def _load_env_vars(self):
        """Load environment variables when first accessed"""
        self._database = getenv('SQL_DATABASE')
        self._database_stage = getenv('SQL_DATABASE_STAGE')

def init_environment(logger=None):
    """
    Initialize environment variables after GUI is ready
    Should be called from FileDialog.__init__ after GUI setup
    
    Args:
        logger: Optional logger instance for error reporting
    """
    from config.env_setup import setup_environment
    if not setup_environment(logger=logger):
        if logger:
            logger.error("Environment setup failed - some database features may not work")

# Path configurations
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
RESOURCES_DIR = BASE_DIR / "resources"
ICON_PATH = RESOURCES_DIR / "favicon.ico"
RULES_FILE = CONFIG_DIR / "config" / "property_rules.yml"
ENV_FILE = CONFIG_DIR / "config" / "db_credentials.env"

# Logging configurations
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_FILENAME_FORMAT = "PackageAutoReview_{timestamp}.log"

# File patterns
SSIS_FILE_TYPES = [("SSIS Package files", "*.dtsx")]
SQL_FILE_TYPES = [("SQL files", "*.sql")]

# Validation patterns
# PACKAGE_DIMENSION_NAME_PATTERNS = []
# PACKAGE_FACT_NAME_PATTERNS = []
TABLE_TYPES = {
    'DIM' : {
        'name_pattern' : re.compile(r"^Fill_Dim\w+$")
    },
    'FACT' : {
        'name_pattern' : re.compile(r"^Fill_Fact\w+$")
    }
}

FRAMEWORK_CONTAINERS = [
    re.compile(r"Stage.*Initialization"),
    re.compile(r"Extract.*Transform.*OLTP"),
    re.compile(r"Load.*Data"),
    re.compile(r"Update.*Config.*Table.*Insert.*Log")
]

# Specific patterns for each package type
PACKAGE_TYPES = {
    'Full Load': {
        'expected_containers': [
            r"Stage.*Initialization",
            r"Extract.*Transform.*OLTP",
            r"Load.*Data",
            r"Update.*Config.*Table.*Insert.*Log"
        ]
    },
    'Incremental': {
        'expected_containers': [
            r"Get.*Record.*Config.*Table",
            r"Stage.*Initialization",
            r"Extract.*Transform.*OLTP",
            r"Load.*Data",
            r"Update.*Config.*Table.*Insert.*Log"
        ]
    }
}

# Specific (extra) SQL Script components
DYNAMIC_VALIDATION_RULES = {
    'FACT': [
        ('Get Last Value', r"Get.*Last.*Value for \w+"),
        ('Get IsFullLoad Value', r"Get.*IsFullLoad.*Value"),
        ('Update ConfigTable', r"Update.*ConfigTable")
    ]
}

# SQL patterns
SQL_TABLE_NAME_PATTERN = re.compile(r"Table Name:\s*(\w+)")
SQL_SECTION_DELIMITER = re.compile(r"\-\-\-+\n")
SQL_USE_STATEMENT = r"(?i)^\s*USE\s+.*\s*;?\s*(\n|$)"
SQL_SECTION_HEADER = r"--(.*?)(\n|$)"

# Component patterns
COMPONENT_PATTERNS = {
    "source": re.compile(r"^Get Data [Ff]rom \w+$"),
    "destination": re.compile(r"^Insert [Ii]nto \w+"),
    "hash": re.compile(r"^Multiple Hash")
}

# XML namespaces
XML_NAMESPACES = {
    'SQLTask': 'www.microsoft.com/sqlserver/dts/tasks/sqltask',
    'DTS': 'www.microsoft.com/SqlServer/Dts'
}

# YAML Config
DEFAULT_YAML_COMMENTS = """\
# Dataflow Component Properties Rules
#
# This YAML file contains validation rules for dataflow pipeline components.
# Each component type has property rules with validation conditions and expected values.
#
# Supported validation conditions:
# - equals: Value must match exactly
# - str_not_empty: Must be a non-empty string
# - is_none: Value must be None/empty
# - regex_match: Value must match regular expression
#
# Rule structure:
# component_type:
#   property_name:
#     condition: validation_type
#     value: expected_value  # (optional)
"""

DEFAULT_PROPERTY_RULES = {
    'oledb_source': {
        'AlwaysUseDefaultCodePage': {'condition': 'equals', 'value': 'false'},
        # 'DefaultCodePage': {'condition': 'equals', 'value': '1252'},
        'SqlCommand': {'condition': 'str_not_empty'},
        'SqlCommandVariable': {'condition': 'is_none'}
    },
    'oracle_source': {
        'DefaultCodePage': {'condition': 'equals', 'value': '1256'},
        'SqlCommand': {'condition': 'str_not_empty'},
        'BatchSize': {'condition': 'equals', 'value': '100000'}
    },
    'oledb_destination': {
        'AlwaysUseDefaultCodePage': {'condition': 'equals', 'value': 'false'},
        # 'DefaultCodePage': {'condition': 'equals', 'value': '1256'},
        'SqlCommand': {'condition': 'is_none'},
        'FastLoadOptions': {'condition': 'is_none'}
    },
    'multiple_hash': {
        'MultipleThreads': {'condition': 'equals', 'value': '0'},
        'SafeNullHandling': {'condition': 'equals', 'value': '1'},
        'IncludeMillsecond': {'condition': 'equals', 'value': '1'},
        'HashType': {'condition': 'equals', 'value': '6'},
        'HashOutputType': {'condition': 'equals', 'value': '0'}
    }
}

# SQL query mappings
"""
`QUERY_DB_MAP` is a dictionary of {regex_pattern:db_name} mapping regex patterns to database names, used to identify the database associated with a specific query name.

IMPORTANT: The order of patterns matters. Earlier patterns take precedence over later ones in case of overlapping matches or being written in the SQL file.
NOTE: If database name is `None`, the `USE` query will be disregarded.

`QUERY_ALIAS_MAP` is a dictionary of {regex_pattern:alias} mapping regex patterns to alias names, used to replace query names with their corresponding aliases.

IMPORTANT: Ensure that regex patterns match exactly between QUERY_DB_MAP and QUERY_ALIAS_MAP when adding new entries.
"""
# Singleton instance
db_config = _DatabaseConfig()
DATABASE = db_config.DATABASE
DATABASE_STAGE = db_config.DATABASE_STAGE
QUERY_DB_MAP = db_config.QUERY_DB_MAP

QUERY_ALIAS_MAP = {
    re.compile(r"^\bGet\s+Last\s+Value\s+for\s+\w+\b$", re.IGNORECASE): "Get Config Record",
    re.compile(r"^\bCreate\s+Table\s+(?:Dim|Fact)\w*Stage\b$", re.IGNORECASE): "Stage Initialization",
    re.compile(r"^\bGet\s+(?:Record|Data)\s+[Ff]rom\s+(?!\w*Stage\b)(\w+)\b", re.IGNORECASE): "Get Record from OLTP",
    re.compile(r"^\bCreate\s+Clustered\s+Index\s+on\s+(?:Dim|Fact)\w*Stage\b$", re.IGNORECASE): "Create Clustered Index on Stage Table",
    re.compile(r"^\bGet\s+(?:Record|Data)\s+from\s+(?:Dim|Fact)\w*Stage\b$", re.IGNORECASE): "Get Data from Stage",
    re.compile(r"^\bUpdate\s+(?:Dim|Fact)(?!\w*Stage\b)(\w+)\b$", re.IGNORECASE): "Update DW Table",
}