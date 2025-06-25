#!/usr/bin/env python3
"""Main entry point for Package Auto Review application."""

import os, sys
from typing import Optional
import re
from gui.file_dialog import FileDialog
from utils.logging import configure_logging
from core.processor import SSISProcessor
from core.validator import PackageValidator
from core.dataflow_analyzer import DataFlowAnalyzer
from core.db_queries import DBQueries
from core.sql_file_builder import SQLFileBuilder
from utils.file_io import load_property_rules, ensure_config_exists

class PackageAutoReview:
    """Main application class orchestrating all components."""
    
    def __init__(self):
        self.logger = configure_logging()
        self.file_dialog: Optional[FileDialog] = None
        self.processor: Optional[SSISProcessor] = None
        self.validator: Optional[PackageValidator] = None
        self.dataflow_analyzer: Optional[DataFlowAnalyzer] = None
        self.db_queries: Optional[DBQueries] = None
        self.sql_file_builder: Optional[SQLFileBuilder] = None

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
            
            # Load SQL file builder
            self.db_queries = DBQueries(self.logger)
            self.sql_file_builder = SQLFileBuilder(self.logger, self.db_queries)

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

        if not ssis_path:
            self.logger.error("File selection cancelled")
            return

        # Data processing
        package_data = self.processor.process_package(ssis_path)
        if package_data['type'] != package_type:
            self.logger.warning(f"Package type mismatch: Expected {package_type}, got {package_data['type']}")
            return

        # Validation
        self.logger.info("Starting package validation...")
        try:
            self.validator.validate(package_data)
            self.logger.info("Package validation completed successfully")
        except Exception as e:
            self.logger.error(f"Package validation failed: {e}")
        finally:
            self.logger.info(f"Package validation process ended")

        # Dataflow analysis
        self.logger.info("Starting dataflow analysis...")
        try:
            self._analyze_dataflows(package_data)
            self.logger.info("Dataflow analysis completed successfully")
        except Exception as e:
            self.logger.error(f"Dataflow analysis failed: {e}")
        finally:
            self.logger.info(f"Dataflow analysis process ended")
        
        # Build SQL file
        self.logger.info("Starting SQL file generation...")
        try:
            self._sql_file_builder(package_data)
            self.logger.info("SQL file generation completed successfully")
        except Exception as e:
            self.logger.error(f"SQL file generation failed: {e}")
        finally:
            self.logger.info(f"SQL file generation process ended")

    def _analyze_dataflows(self, package_data: dict) -> None:
        """Analyze all dataflows in the package."""
        components = package_data['structure']['components']
        pattern_stage_db = re.compile(r".*Extract.*Transform.*OLTP.*")
        pattern_dw_db = re.compile(r".*Load.*Data.*")

        pipelines = []
        for path, component in components.items():
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

    def _sql_file_builder(self, package_data: dict) -> None:
        """Build a SQL file containing all SQL queries used in the SSIS package."""
        self.sql_file_builder.sql_query_extractor(package_data)

        if self.sql_file_builder.sql_queries:
            self.logger.debug("Extracted queries:")
            for item in self.sql_file_builder.sql_queries:
                for name, query in item.items():
                    self.logger.debug(f"Query {name}:\n{query}")
        else:
            self.logger.warning(f"No SQL queries were extracted")

        queries_dict = {list(item.keys())[0]: list(item.values())[0] for item in self.sql_file_builder.sql_queries}

        # SQL file selection
        sql_path = self.file_dialog.get_sql_path()
        generate_sql = self.file_dialog.generate_sql_var.get()
        if generate_sql and not sql_path:
            self.logger.error("Insert Null record SQL script path is not set")
            return

        # Generate SQL file
        self.sql_file_builder.insert_null_script_path = sql_path
        output_file_path = os.path.join(os.getcwd(), f"{package_data['metadata'].get('name')}.sql")
        self.sql_file_builder.generate_sql_file(
            package_data=package_data,
            queries_dict=queries_dict,
            output_file_path = output_file_path
        )

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.file_dialog:
            self.file_dialog.cleanup()
        self.logger.info("Application shutdown complete")

if __name__ == "__main__":
    app = PackageAutoReview()
    app.run()
    input("Press ENTER to continue")