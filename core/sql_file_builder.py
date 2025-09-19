import os
from typing import Dict, Optional
from utils.helpers import get_xpath, beautify_sql_query, resolve_connection_id
from config.constants import (
    XML_NAMESPACES,
    QUERY_ALIAS_MAP,
    db_config
)
from core.db_queries import DBQueries


class SQLFileBuilder:
    def __init__(self, logger, db_queries: Optional[DBQueries] = None) -> None:
        self.logger = logger
        self.namespaces = XML_NAMESPACES
        self.query_db_map = db_config.QUERY_DB_MAP
        self.query_alias_map = QUERY_ALIAS_MAP
        self.db_queries = db_queries or DBQueries(self.logger)
        self.datawarehouse = db_config.DATABASE
        self.insert_null_script_path = None
        self.sql_queries = []

    def sql_query_extractor(self, package_data: Dict):
        """
        Extract SQL queries from components within an SSIS package.

        Args:
            package_data (Dict): A dictionary containing structured package data,
                                 including 'structure', 'tree', and 'type'.
        """
        components = package_data['structure'].get('components', {})

        for key, value in components.items():
            component_type = value.get('type')
            if component_type == 'Microsoft.ExecuteSQLTask':
                self._extract_from_execute_sql_task(key, value, package_data)

            elif component_type == 'Microsoft.Pipeline':
                pipeline_type = package_data.get('type')
                if pipeline_type == 'FACT':
                    if self._has_property_expression(package_data, key):
                        self._extract_from_variable_expressions(package_data, key)
                    else:
                        self._extract_from_sql_command(package_data, key, is_fact=True)
                elif pipeline_type == 'DIM':
                    self._extract_from_sql_command(package_data, key, is_fact=False)

    def _has_property_expression(self, package_data: Dict, key: str) -> bool:
        """Check if the component contains a PropertyExpression."""
        element = package_data['tree'].find(key)
        return element.find('.//DTS:PropertyExpression', namespaces=self.namespaces) is not None

    def _extract_from_execute_sql_task(self, key: str, value: Dict, package_data: Dict):
        """Extract SQL query from an ExecuteSQLTask component."""
        name = value.get('name')
        connections_map = package_data['structure'].get('connections', {})
        try:
            sql_query = get_xpath(
                package_data['tree'].find(key),
                './/SQLTask:SqlTaskData/@SQLTask:SqlStatementSource',
                self.namespaces
            )
            # Find DB Name
            connection_id = get_xpath(
                package_data['tree'].find(key),
                './/SQLTask:SqlTaskData/@SQLTask:Connection',
                self.namespaces
            )
            sql_query_db = resolve_connection_id(connection_id, connections_map, logger=self.logger)

            self.sql_queries.append({name: f"USE {sql_query_db}\nGO\n" + sql_query})
        except Exception as e:
            self.logger.error(f"Failed to extract SQL query from '{name}': {e}")

    def _extract_from_variable_expressions(self, package_data: Dict, key: str):
        """Extract SQL queries from variable expressions."""
        self.logger.debug("Extracting queries from variables")
        variables = package_data['structure'].get('variables', [])
        for variable in variables:
            name = variable.get('{www.microsoft.com/SqlServer/Dts}ObjectName')
            sql_query = variable.get('{www.microsoft.com/SqlServer/Dts}Expression')
            try:
                sql_query = sql_query.strip('"') if sql_query else ""
            except Exception as e:
                self.logger.error(f"Query extraction for '{name}' failed with error:\n{e}")
                continue

            self.sql_queries.append({name: sql_query})

    def _extract_from_sql_command(self, package_data: Dict, key: str, is_fact: bool):
        """Extract SQL queries from SqlCommand property."""
        self.logger.debug("Extracting queries from SQL command property")
        element = package_data['tree'].find(key)
        connections_map = package_data['structure'].get('connections', {})
        for component in element.xpath('.//component'):
            name = component.get('name')
            sql_element = component.xpath('.//property[@name="SqlCommand"]')

            if not sql_element:
                continue

            sql_query = sql_element[0].text or ""
            access_mode = component.xpath('.//property[@name="AccessMode"]')[0].text
            connection_id = component.xpath('.//connection/@connectionManagerID')[0]
            try:
                sql_query = sql_query.strip()
                if (not sql_query) and (access_mode in ('1', '2')):
                    self.logger.warning(f"'SqlCommand' exists for '{name}', but it's empty. Verify the source.")
                    continue
            except Exception as e:
                self.logger.error(f"Query extraction for '{name}' failed with error:\n{e}")
                continue

            if access_mode in ('1', '2'):
                sql_query_db = resolve_connection_id(connection_id, connections_map, logger=self.logger)
                self.sql_queries.append({name: f"USE {sql_query_db}\nGO\n" + sql_query})

    def generate_sql_file(self, package_data, queries_dict, output_file_path=None, sort_order=None):
        """
        Generates a SQL file containing DDL statements and original queries for tables sorted in a specified order.

        Args:
            package_data (dict): Dictionary of SSIS package data
            queries_dict (dict): Dictionary of {table_name: SQL_query_string}
            output_file_path (str) [Optional]: Path to the output SQL file
            sort_order (dict) [Optional]: Dictionary of {regex_pattern:db_name} specifying the processing order and the associated database name
        """
        if sort_order is None:
            sort_order = self.query_db_map

        if output_file_path is None:
            output_file_path = os.path.join(os.getcwd(), f"{package_data['metadata'].get('name')}.sql")

        # Validate input dictionaries
        missing_tables = [
            query_name
            for query_name in queries_dict
            if not any(pattern.match(query_name) for pattern in sort_order)
        ]
        if missing_tables:
            self.logger.warning(
                f"Unrecognized queries: {', '.join(missing_tables)}")

        # Prepare sorted table list based on sort_order
        sorted_queries = [
            query_name
            for pattern in sort_order
            for query_name in queries_dict if pattern.match(query_name)
        ]

        include_null_record = (package_data['type'] == 'DIM')

        sql_lines = []

        try:
            # Fetch table creation DDL
            sql_lines.append("/*")
            sql_lines.append(f"Table Name: {package_data['metadata'].get('table_name')}")
            sql_lines.append(f"Creation Date: {package_data['metadata'].get('creation_date')}")
            sql_lines.append(f"Creator Name: {package_data['metadata'].get('creator_name')}")
            sql_lines.append("*/")
            sql_lines.append("\n")

            self.logger.info("Fetching table creation DDL...")
            ddl_statements = self.db_queries.get_table_definition(table=package_data['metadata'].get('table_name'), schema='dbo') or ""
            sql_lines.append("---------------------------------------------------------------------------")
            sql_lines.append("-- Create DW Table")
            sql_lines.append(f"USE {self.datawarehouse}\nGO\n")
            sql_lines.append(beautify_sql_query(ddl_statements))
            sql_lines.append("\n")
            self.logger.info("Table creation DDL insertion completed")

            for query_name in sorted_queries:
                self.logger.info(f"Inserting '{query_name}' query...")
                query_name_alias = self._get_query_alias(query_name, self.query_db_map, self.query_alias_map)
                # Append DDL statements and original query
                sql_lines.append("---------------------------------------------------------------------------")
                sql_lines.append(f"-- '{query_name_alias}'")
                beautified_query = beautify_sql_query(queries_dict[query_name].strip())
                sql_lines.append(beautified_query)
                sql_lines.append("\n")
                self.logger.info(f"'{query_name}' query insertion completed")

            # Find Null record insertion query
            if include_null_record:
                self.logger.info(f"Checking the existence of Null record insertion query...")
                with open(self.insert_null_script_path, 'r', encoding='utf-16') as f:
                    insull_sql_content = f.read()
                table_name = package_data['metadata'].get('table_name')
                insert_null_query = self.db_queries.find_insert_statement(insull_sql_content, table_name)
                if insert_null_query:
                    sql_lines.append("---------------------------------------------------------------------------")
                    sql_lines.append("-- Insert Record for Null Values")
                    sql_lines.append(f"USE {self.datawarehouse}\nGO\n")
                    beautified_query = beautify_sql_query(insert_null_query)
                    sql_lines.append(beautified_query)
                self.logger.info(f"'Insert Record for Null Values' query insertion completed")

            # Write to output file
            with open(output_file_path, 'w', encoding='utf-16') as sql_file:
                sql_file.write("\n".join(sql_lines))
        except Exception as e:
            self.logger.error(f"An error occured while creating the .sql file:\n{e}")

    def _get_query_alias(self, query, query_db_map, query_alias_map):
        """Function to get alias names for matching queries"""
        for pattern in query_db_map:
            if pattern.match(query):
                # Check if the pattern exists in QUERY_ALIAS_MAP
                if pattern in query_alias_map:
                    return query_alias_map[pattern]
                else:
                    return query  # Return the original query if no alias is found
        return None

    # def _get_database_name(self, query, query_db_map):
    #     """Function to get the database name for a query"""
    #     for pattern, db_name in query_db_map.items():
    #         if pattern.match(query):
    #             return db_name  # Return the database name if a match is found
    #     return None
