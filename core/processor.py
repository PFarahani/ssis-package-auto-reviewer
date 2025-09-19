from lxml import etree
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from config.constants import (
    XML_NAMESPACES,
    PACKAGE_TYPES
)
from utils.helpers import (
    validate_pattern,
    get_xpath,
    detect_package_type
)
import re


class SSISProcessor:
    def __init__(self, logger):
        self.logger = logger
        self.namespaces = XML_NAMESPACES
        self.package_type = None

    def process_package(self, file_path: Path) -> Dict[str, Any]:
        """Process SSIS package file and return structured data."""
        self.logger.info("Starting package processing")
        tree = etree.parse(file_path)
        root = tree.getroot()

        package_name = get_xpath(root, '@DTS:ObjectName', self.namespaces)
        self.package_type = detect_package_type(package_name, self.logger)

        return {
            'metadata': self._extract_package_metadata(root),
            'structure': self._analyze_package_structure(root),
            'tree': tree,
            'type': self.package_type
        }

    def _extract_package_metadata(self, root) -> Dict[str, str]:
        """Extract core package metadata."""
        metadata = {
            'name': get_xpath(root, '@DTS:ObjectName', self.namespaces),
            'table_name': get_xpath(root, '@DTS:ObjectName', self.namespaces).removeprefix("Fill_"),
            'version': get_xpath(root, '@DTS:VersionMajor', self.namespaces),
            'creation_date': datetime.strptime(get_xpath(root, '@DTS:CreationDate', self.namespaces), '%m/%d/%Y %I:%M:%S %p').strftime('%Y-%m-%d %H:%M:%S'),
            'creator_name': get_xpath(root, '@DTS:CreatorName', self.namespaces).split("\\")[-1]
        }

        self.logger.info("Validating package name")
        pattern = PACKAGE_TYPES[self.package_type]['name_pattern']
        validate_pattern(
            metadata['name'],
            [re.compile(pattern)],
            self.logger)
        return metadata

    def _analyze_package_structure(self, root) -> Dict[str, Any]:
        """Analyze package structure and components."""
        structure = {
            'containers': [],
            'components': {},
            'variables': self._find_variables(root),
            'parameters': self._find_parameters(root),
            'connections': self._find_connections(root)
        }

        executables = root.find('.//DTS:Executables', self.namespaces)
        for elem in executables.findall('.//DTS:Executable', self.namespaces):
            elem_path = elem.getroottree().getelementpath(elem)
            elem_type = get_xpath(elem, '@DTS:ExecutableType', self.namespaces)
            elem_name = get_xpath(elem, '@DTS:ObjectName', self.namespaces)

            structure['components'][elem_path] = {
                'name': elem_name,
                'type': elem_type
            }

            if elem_type == "STOCK:SEQUENCE":
                structure['containers'].append(elem_name)

        return structure

    def _find_variables(self, root) -> list:
        """Find and return package variables."""
        try:
            return [v.attrib for v in root.xpath('.//DTS:Variable', namespaces=self.namespaces)]
        except AttributeError:
            return []

    def _find_parameters(self, root) -> list:
        """Find and return package parameters."""
        try:
            return [p.attrib for p in root.xpath('.//DTS:PackageParameter', namespaces=self.namespaces)]
        except AttributeError:
            return []

    def _find_connections(self, root) -> dict:
        """Find and return package connections."""
        try:
            connections = root.xpath('.//connections/connection', namespaces=self.namespaces)
            result = {}

            for conn in connections:
                conn_id_raw = conn.get("connectionManagerID", "")
                conn_ref_raw = conn.get("connectionManagerRefId", "")

                # Extract connection ID
                id_match = re.search(r"\{(.+?)\}", conn_id_raw)
                conn_id = id_match.group(1) if id_match else None

                # Extract connection name
                ref_match = re.search(r"\[(.+?)\]", conn_ref_raw)
                conn_ref = ref_match.group(1) if ref_match else None

                if conn_id and conn_ref:
                    result[conn_id] = conn_ref

            return result

        except AttributeError:
            return {}
