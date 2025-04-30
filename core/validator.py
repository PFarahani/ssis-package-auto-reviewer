import re
from typing import Dict
from config.constants import XML_NAMESPACES, PACKAGE_TYPES, DYNAMIC_VALIDATION_RULES
from utils.helpers import compare_texts

class PackageValidator:
    def __init__(self, logger):
        self.logger = logger

    def validate(self, package_data: Dict, sql_data: Dict) -> None:
        """Main validation entry point."""
        self.logger.info("Starting package validation")
        is_incremental = self._check_incremental(package_data)
        self._validate_package_structure(package_data, is_incremental)
        self._validate_sql_consistency(package_data, sql_data, is_incremental)
        self._validate_dataflows(package_data)
        if is_incremental:
            self.logger.info("Running inncremental package specific validations")
            self._validate_incremental_variables(package_data, sql_data)

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

    def _validate_incremental_variables(self, package_data: Dict, sql_data: Dict) -> None:
        """Validate required variables for incremental packages."""
        required_vars = {
            'V_FullLoadQuery': sql_data['sections'].get('V_FullLoadQuery'),
            'V_IncrementalQuery': sql_data['sections'].get('V_IncrementalQuery'),
            'V_Query': sql_data['sections'].get('V_Query'),
            'V_LastValue': '1900-01-01 00:00:00'
        }
        
        variables = {v['{www.microsoft.com/SqlServer/Dts}ObjectName']: v.get('{www.microsoft.com/SqlServer/Dts}Expression') 
                   for v in package_data['structure']['variables']}

        for var_name, expected_value in required_vars.items():
            if var_name not in variables:
                self.logger.error(f"Missing required incremental variable: {var_name}")
            elif expected_value and variables[var_name] != expected_value:
                self.logger.warning(
                    f"Variable {var_name} has non-default value. "
                    f"Expected: {expected_value}, Found: {variables[var_name]}"
                )

    def _validate_sql_consistency(self, package_data: Dict, sql_data: Dict, is_incremental: bool) -> None:
        """Validate consistency between SQL file and package."""
        expected_table = package_data['metadata']['name'].removeprefix('Fill_')
        if sql_data['table_name'] != expected_table:
            raise ValueError(
                f"SQL table {sql_data['table_name']} "
                f"doesn't match package {expected_table}"
            )

        self._validate_sql_sections(package_data, sql_data, is_incremental)

    def _validate_sql_sections(self, package_data: Dict, sql_data: Dict, is_incremental: bool) -> None:
        """Validate SQL queries against package components."""
        tree = package_data['tree']
        namespaces = XML_NAMESPACES

        # Validate Stage Initialization
        stage_init = next((k for k, v in package_data['structure']['components'].items() 
                        if re.match(r"Stage.*Initialization", v['name'])), None)
        if stage_init:
            self._compare_sql_queries(
                tree.find(stage_init),
                sql_data['sections']['Stage Initialization'],
                'Stage Initialization'
            )

        # Validate other SQL sections
        sections_to_validate = [
            ('Create Clustered Index', r"Create Clustered Index on \w+Stage"),
            ('Update IsExists', r"Update IsExists"),
            ('Insert PackageLog', r"Insert PackageLog")
        ]

        if (is_incremental and package_data['type'] in DYNAMIC_VALIDATION_RULES):
            sections_to_validate.extend(DYNAMIC_VALIDATION_RULES[package_data['type']])

        for section_name, pattern in sections_to_validate:
            component = next((k for k, v in package_data['structure']['components'].items()
                            if re.match(pattern, v['name'])), None)
            if component and section_name in sql_data['sections']:
                self._compare_sql_queries(
                    tree.find(component),
                    sql_data['sections'][section_name],
                    section_name
                )

    def _compare_sql_queries(self, component, expected_query: str, section_name: str) -> None:
        """Compare component SQL with reference query."""
        actual_query = component.find('.//SQLTask:SqlTaskData', XML_NAMESPACES).xpath(
            '@SQLTask:SqlStatementSource', namespaces=XML_NAMESPACES)[0]
        similarity = compare_texts(actual_query, expected_query)
        
        if similarity == 100:
            self.logger.info(f"{section_name} queries match exactly")
        else:
            self.logger.warning(
                f"{section_name} queries similarity: {similarity}%"
            )

    def _validate_dataflows(self, package_data: Dict) -> None:
        """Validate data flow components."""
        # Implementation would call DataFlowAnalyzer
        pass