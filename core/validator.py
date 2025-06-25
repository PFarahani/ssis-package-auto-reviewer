import re
from typing import Dict
from config.constants import PACKAGE_TYPES

class PackageValidator:
    def __init__(self, logger):
        self.logger = logger

    def validate(self, package_data: Dict) -> None:
        """Main validation entry point."""
        self.logger.info("Starting package validation")
        is_incremental = self._check_incremental(package_data)
        self._validate_package_structure(package_data, is_incremental)
        self._validate_dataflows(package_data)

    def _check_incremental(self, package_data: Dict) -> bool:
        """Check if package uses incremental loading pattern."""
        has_config_component = any(
            re.match(r"Get.*Config.*Table", v['name'])
            for v in package_data['structure']['components'].values()
        )
        
        if has_config_component:
            self.logger.info("Package uses incremental loading pattern")
            return True
        return False

    def _validate_package_structure(self, package_data: Dict, is_incremental: bool) -> None:
        """Validate overall package structure."""
        expected_containers = PACKAGE_TYPES[package_data['type']]['expected_containers']
        containers = package_data['structure']['containers']

        # Filter out config table check if not incremental
        if not is_incremental:
            expected_containers = [
                pattern for pattern in expected_containers
                if not re.match(r"Get.*Record.*Config.*Table", pattern)
            ]

        missing = [
            pattern for pattern in expected_containers
            if not any(re.match(pattern, c) for c in containers)
        ]
        
        if missing:
            self.logger.warning(f"Missing required containers: {missing}")

        if (package_data['structure']['variables'] and not is_incremental):
            self.logger.warning("Package contains variables which are not recommended")

        if package_data['structure']['parameters']:
            self.logger.warning("Package contains parameters which are not recommended")

    def _validate_dataflows(self, package_data: Dict) -> None:
        """Validate data flow components."""
        # Implementation would call DataFlowAnalyzer
        pass