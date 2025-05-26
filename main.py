#!/usr/bin/env python3
"""Main entry point for Package Auto Review application."""

import sys
from typing import Optional
import re
from gui.file_dialog import FileDialog
from utils.logging import configure_logging
from core.processor import SSISProcessor
from core.validator import PackageValidator
from core.dataflow_analyzer import DataFlowAnalyzer
from utils.file_io import load_property_rules, ensure_config_exists

class PackageAutoReview:
    """Main application class orchestrating all components."""
    
    def __init__(self):
        self.logger = configure_logging()
        self.file_dialog: Optional[FileDialog] = None
        self.processor: Optional[SSISProcessor] = None
        self.validator: Optional[PackageValidator] = None
        self.dataflow_analyzer: Optional[DataFlowAnalyzer] = None

    def initialize(self) -> None:
        """Initialize application components."""
        try:
            # Ensure configuration exists
            ensure_config_exists()
            
            # Initialize components
            self.file_dialog = FileDialog(self.logger)
            self.processor = SSISProcessor(self.logger)
            self.validator = PackageValidator(self.logger)
            
            # Load property rules for dataflow analysis
            property_rules = load_property_rules()
            self.dataflow_analyzer = DataFlowAnalyzer(self.logger, property_rules)

        except Exception as e:
            self.logger.critical("Initialization failed: %s", str(e))
            raise

    def run(self) -> None:
        """Main execution flow."""
        try:
            self.initialize()
            self._main_workflow()
        except KeyboardInterrupt:
            self.logger.info("Operation cancelled by user")
            sys.exit(1)
        except Exception as e:
            self.logger.error("Fatal error occurred: %s", str(e), exc_info=True)
            sys.exit(1)
        finally:
            self.cleanup()

    def _main_workflow(self) -> None:
        """Core application workflow."""
        # Get package type first
        package_type = self.file_dialog.get_package_type()

        # File selection
        ssis_path = self.file_dialog.get_ssis_path()
        sql_path = self.file_dialog.get_sql_path()

        if not ssis_path or not sql_path:
            self.logger.error("File selection cancelled")
            return

        # Data processing
        package_data = self.processor.process_package(ssis_path)
        if package_data['type'] != package_type:
            self.logger.warning(f"Package type mismatch: Expected {package_type}, got {package_data['type']}")
            return

        sql_data = self.processor.process_sql(sql_path)

        # Validation
        self.validator.validate(package_data, sql_data)
        
        # Dataflow analysis
        self._analyze_dataflows(package_data)

        self.logger.info("Package review completed successfully")

    def _analyze_dataflows(self, package_data: dict) -> None:
        """Analyze all dataflows in the package."""
        containers = package_data['structure']['components']
        pattern_stage_db = re.compile(r".*Extract.*Transform.*OLTP.*")
        pattern_dw_db = re.compile(r".*Load.*Data.*")

        pipelines = []
        for path, component in containers.items():
            if component['type'] == 'Microsoft.Pipeline':
                pipeline_node = package_data['tree'].find(path)
                ref_id = pipeline_node.attrib.get('{www.microsoft.com/SqlServer/Dts}refId', '')
                pipelines.append((ref_id, pipeline_node))

        def _get_priority(item):
            ref_id = item[0]
            if pattern_stage_db.match(ref_id):
                return 0
            elif pattern_dw_db.match(ref_id):
                return 1
            else:
                return 2 
        
        # Sort pipelines by priority
        pipelines.sort(key=_get_priority)

        for _, pipeline_node in pipelines:
            self.dataflow_analyzer.analyze(pipeline_node.find('.//pipeline'))

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.file_dialog:
            self.file_dialog.cleanup()
        self.logger.info("Application shutdown complete")

if __name__ == "__main__":
    app = PackageAutoReview()
    app.run()
    input("Press ENTER to continue")