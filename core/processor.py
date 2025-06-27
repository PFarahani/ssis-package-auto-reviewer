from lxml import etree
from typing import Dict, Any
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
            'version': get_xpath(root, '@DTS:VersionMajor', self.namespaces),
            'creation_date': get_xpath(root, '@DTS:CreationDate', self.namespaces)
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
            'parameters': self._find_parameters(root)
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
