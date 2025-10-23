from typing import Dict
from config.constants import COMPONENT_PATTERNS
from utils.helpers import validate_pattern

class DataFlowAnalyzer:
    def __init__(self, logger, property_rules: Dict):
        self.logger = logger
        self.property_rules = property_rules
        self.source_columns = {}

    def analyze(self, pipeline_element) -> None:
        """Analyze data flow components in pipeline."""
        self.logger.info("Starting data flow analysis")
        
        if pipeline_element.get("autoAdjustBufferSize") != 'true':
            self.logger.warning("'AutoAdjustBufferSize' not enabled")

        components = pipeline_element.find('.//components')
        if components is None:
            self.logger.warning("No components found in pipeline")
            return

        sorted_components = sorted(
            components,
            key=lambda c: 0
            if (c.attrib.get('componentClassID') == 'Microsoft.OLEDBSource' or
            c.attrib.get('componentClassID') == 'Microsoft.SSISOracleSrc') else 1
            )

        for component in sorted_components:
            component_type = component.attrib.get('componentClassID', 'unknown')
            component_name = component.attrib.get('name', 'unnamed')
            
            self.logger.debug(f"Analyzing {component_type} - {component_name}")
            
            if component_type == 'Microsoft.OLEDBSource':
                self._analyze_oledb_source(component, component_name)
            elif component_type == 'Microsoft.SSISOracleSrc':
                self._analyze_oracle_source(component, component_name)
            elif component_type == 'Microsoft.OLEDBDestination':
                self._analyze_oledb_destination(component, component_name)
            elif 'MultipleHash' in component_type:
                self._analyze_multiple_hash(component, component_name)

    def _analyze_oracle_source(self, component, component_name) -> None:
        """Validate Oracle Source components."""
        self._validate_component_name(component, 'source')
        properties = self._extract_properties(component)
        self._check_property_compliance(properties, component_name, 'oracle_source')

        # Capture output columns for downstream validation
        self.source_columns = {
            col.attrib['name']: col.attrib['dataType']
            for col in component.findall('.//outputColumn')
        }

    def _analyze_oledb_source(self, component, component_name) -> None:
        """Validate OLEDB Source components."""
        self._validate_component_name(component, 'source')
        properties = self._extract_properties(component)
        self._check_property_compliance(properties, component_name, 'oledb_source')

        # Capture output columns for downstream validation
        self.source_columns = {
            col.attrib['name']: col.attrib['dataType']
            for col in component.findall('.//outputColumn')
        }

    def _analyze_oledb_destination(self, component, component_name) -> None:
        """Validate OLEDB Destination components."""
        self._validate_component_name(component, 'destination')
        properties = self._extract_properties(component)
        self._check_property_compliance(properties, component_name, 'oledb_destination')
        self._check_column_mapping(component, component_name)

    def _analyze_multiple_hash(self, component, component_name) -> None:
        """Validate Multiple Hash components."""
        self._validate_component_name(component, 'hash')
        properties = self._extract_properties(component)
        self._check_property_compliance(properties, component_name, 'multiple_hash')
        self._check_column_selection(component, component_name)

    def _validate_component_name(self, component, component_type: str) -> None:
        """Validate component name against patterns."""
        name = component.attrib.get('name', '')
        pattern = COMPONENT_PATTERNS.get(component_type)
        if not validate_pattern(name, [pattern], self.logger):
            self.logger.warning(f"Invalid {component_type} name: {name}")

    def _extract_properties(self, component) -> Dict[str, str]:
        """Extract component properties as key-value pairs."""
        return {
            prop.attrib['name']: prop.text
            for prop in component.findall('.//property')
        }

    def _check_property_compliance(self, properties: Dict, component_name: str, rule_set: str) -> None:
        """Validate properties against configured rules."""
        rules = self.property_rules.get(rule_set, {})
        for prop, (condition, *args) in rules.items():
            value = properties.get(prop)

            if condition == 'equals':
                if value != args[0]:
                    self.logger.warning(
                        f"'{component_name}': Property {prop} should be {args[0]}, found {value}"
                    )
            elif condition == 'str_not_empty':
                if not (isinstance(value, str) and value.strip()):
                    self.logger.warning(
                        f"'{component_name}': Property {prop} should be non-empty string"
                    )
            elif condition == 'is_none':
                if value is not None:
                    self.logger.warning(
                        f"'{component_name}': Property {prop} should be empty, found {value}"
                    )

    def _check_column_mapping(self, component, component_name) -> None:
        """Validate destination column mapping."""
        input_columns = {
            col.attrib.get('cachedName'): col.attrib.get('cachedDataType')
            for col in component.findall('.//inputColumn')
        }
        
        mapped_columns = {
            col.attrib['name']: col.attrib['dataType']
            for col in component.findall('.//externalMetadataColumn')
        }
        
        input_lower = {col.lower() for col in input_columns.keys()}

        missing = {col for col in mapped_columns.keys() if col.lower() not in input_lower}
        if missing:
            self.logger.warning(f"Unmapped columns detected in '{component_name}': {missing}")

    def _check_column_selection(self, component, component_name) -> None:
        """Validate selected columns in transformation components."""
        selected_columns = {
            col.attrib['cachedName']: col.attrib['cachedDataType']
            for col in component.findall('.//inputColumn')
        }
        selected_columns_lower = {col.lower() for col in selected_columns.keys()}

        unselected = {col for col in self.source_columns.keys() if col.lower() not in selected_columns_lower}
        if unselected:
            self.logger.warning(f"Unselected columns detected in '{component_name}': {unselected}")