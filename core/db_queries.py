import os, sys
import pyodbc
import re
from config.env_setup import setup_environment


class DBQueries:
    def __init__(self, logger) -> None:
        self.logger = logger
        from config.constants import db_config
        if not db_config._initialized:
            raise RuntimeError("Database configuration not initialized")

        env_file = 'db_credentials.env'

        if not setup_environment(
            env_file=env_file,
            required_vars=['SQL_SERVER', 'SQL_PORT', 'SQL_DATABASE', 'SQL_USERNAME', 'SQL_PASSWORD'],
            template={
                '#': 'Database credentials',
                'SQL_SERVER': '',
                'SQL_PORT': '1433',
                'SQL_DATABASE': '',
                'SQL_DATABASE_STAGE': '',
                'SQL_USERNAME': '',
                'SQL_PASSWORD': ''
            },
            logger=self.logger
        ):
            raise RuntimeError("Environment setup failed. Please check the configuration.")


    def get_table_definition(self, table, schema='dbo') -> str:
        """
        Generates the DDL script for a specified SQL Server table.

        Args:        
            table: The name of the table.
            schema: The schema of the table. Defaults to 'dbo'.

        Returns:
            A string containing the DDL script, including:
            - `DROP TABLE IF EXISTS` (if applicable).
            - `CREATE TABLE` with column definitions, constraints, and filegroup info.
            - Index definitions with optional data compression and filegroup details.
        """
        server = os.getenv('SQL_SERVER')
        port = os.getenv('SQL_PORT')
        database = os.getenv('SQL_DATABASE')
        username = os.getenv('SQL_USERNAME')
        password = os.getenv('SQL_PASSWORD')

        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server},{port};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
        )

        table = table.removeprefix('Fill_')

        try:
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()

            # Get table definition
            cursor.execute(f"""
            SELECT
                t.name                                                                            AS TableName,
                c.name                                                                            AS ColumnName,
                UPPER(ty.name)                                                                    AS DataType,
                CASE
                    WHEN ty.name IN ('nvarchar', 'nchar') THEN c.max_length / 2
                    WHEN ty.name IN ('varchar', 'char', 'varbinary', 'binary') THEN c.max_length
                    WHEN ty.name IN ('decimal', 'numeric') THEN c.precision
                    END                                                                           AS Length,
                CASE
                    WHEN ty.name IN ('decimal', 'numeric', 'datetime2') THEN c.scale
                    END                                                                           AS Scale,
                c.is_nullable                                                                     AS IsNullable,
                i.name                                                                            AS IndexName,
                i.type_desc                                                                       AS IndexType,
                IIF(EXISTS (SELECT 1
                            FROM sys.key_constraints kc
                                        INNER JOIN sys.indexes pk
                                                ON kc.parent_object_id = pk.object_id AND kc.unique_index_id = pk.index_id
                                        INNER JOIN sys.index_columns ic_pk
                                                ON pk.object_id = ic_pk.object_id AND pk.index_id = ic_pk.index_id
                            WHERE kc.type = 'PK'
                                AND ic_pk.object_id = c.object_id
                                AND ic_pk.column_id = c.column_id), CAST(1 AS BIT), CAST(0 AS BIT)) AS IsPrimaryKey,
                p.data_compression_desc                                                           AS DataCompression,
                fg.name                                                                           AS FileGroupName
            FROM sys.tables t
                    INNER JOIN
                sys.columns c ON t.object_id = c.object_id
                    INNER JOIN
                sys.types ty ON c.user_type_id = ty.user_type_id
                    LEFT JOIN
                sys.index_columns ic ON c.object_id = ic.object_id AND c.column_id = ic.column_id
                    LEFT JOIN
                sys.indexes i ON ic.object_id = i.object_id AND ic.index_id = i.index_id
                    LEFT JOIN
                sys.partitions p ON t.object_id = p.object_id AND i.index_id = p.index_id
                    LEFT JOIN
                    sys.filegroups fg ON i.data_space_id = fg.data_space_id
            WHERE c.object_id = OBJECT_ID('[{schema}].[{table}]')
            ORDER BY t.name, c.column_id, i.name
            """)

            columns = cursor.fetchall()

            # Build CREATE TABLE statement
            ddl = f"DROP TABLE IF EXISTS [{schema}].[{table}]\nGO\n"
            ddl = f"CREATE TABLE [{schema}].[{table}] (\n"
            for col in columns:
                col_def = f"\t[{col.ColumnName}] {col.DataType}"
                # Data types length/precision/scale
                if col.DataType.lower() in ('varchar', 'nvarchar', 'char', 'nchar', 'varbinary'):
                    col_def += f"({col.Length if col.Length != -1 else 'MAX'})"
                elif col.DataType.lower() in ('decimal', 'numeric'):
                    col_def += f"({col.Length},{col.Scale})"
                elif col.DataType.lower() in ('datetime2', 'datetimeoffset', 'time'):
                    col_def += f"({col.Scale})"
                # NOT NULL
                col_def += " NOT NULL" if (
                    not col.IsNullable and not col.IsPrimaryKey) else ""
                # DataCompression
                if col.IsPrimaryKey and not col.DataCompression:
                    col_def += f" PRIMARY KEY {col.IndexType}"
                elif col.IsPrimaryKey and col.DataCompression:
                    col_def += f" PRIMARY KEY {col.IndexType} WITH (DATA_COMPRESSION = {col.DataCompression})"

                ddl += col_def + ",\n"

            ddl = ddl.rstrip(",\n")

            # Find the matching FileGroupName for the primary key
            pk_file_group = next(
                (row[10] for row in columns if row[7]
                == 'NONCLUSTERED' and row[8] == True),
                None
            )
            # Find the matching DataCompression for the primary key
            pk_data_compression = next(
                (row[9] for row in columns if row[7] == 'NONCLUSTERED' and row[8] == True),
                None
            )

            # Table's (NONCLUSTERED indexes) FileGroup
            ddl += f"\n) ON {pk_file_group}" if pk_file_group else "\n)"
            # Table's (NONCLUSTERED indexes) DataCompression
            ddl += f" WITH (DATA_COMPRESSION = {pk_data_compression})" if pk_data_compression else ""

            # Get indexes
            cursor.execute(f"""
            SELECT i.name                                                                               AS IndexName,
                i.type_desc                                                                          AS IndexType,
                STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal)                      AS KeyColumns,
                IIF(EXISTS (SELECT 1
                            FROM sys.key_constraints kc
                                        INNER JOIN sys.indexes pk
                                                ON kc.parent_object_id = pk.object_id AND kc.unique_index_id = pk.index_id
                                        INNER JOIN sys.index_columns ic_pk
                                                ON pk.object_id = ic_pk.object_id AND pk.index_id = ic_pk.index_id
                            WHERE kc.type = 'PK'
                                AND ic_pk.object_id = c.object_id
                                AND ic_pk.column_id = c.column_id), CAST(1 AS BIT), CAST(0 AS BIT))  AS IsPrimaryKey,
                p.data_compression_desc                                                              AS DataCompression,
                fg.name                                                                              AS FileGroupName
            FROM sys.indexes i
                    INNER JOIN
                sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
                    INNER JOIN
                sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
                    LEFT JOIN
                sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
                    LEFT JOIN
                sys.filegroups fg ON i.data_space_id = fg.data_space_id
            WHERE i.object_id = OBJECT_ID('[{schema}].[{table}]') AND i.type > 0
            GROUP BY i.name, i.type_desc, p.data_compression_desc, c.object_id, c.column_id, fg.name
            """)

            indexes = cursor.fetchall()
            found_non_pk = False
            for idx in indexes:
                if not idx.IsPrimaryKey:
                    found_non_pk = True
                    ddl += f"\nGO\nCREATE {idx.IndexType} INDEX [{idx.IndexName}] ON [{schema}].[{table}] ({idx.KeyColumns})"
                    ddl += f" WITH (DATA_COMPRESSION = {idx.DataCompression})" if idx.DataCompression else ""
                    ddl += f" ON {idx.FileGroupName}" if idx.FileGroupName else ""
                    ddl += "\nGO\n"
            if not found_non_pk:
                self.logger.warning(f"Skipped scripting indexes: no eligible indexes found (excluding primary key)")
            return ddl

        except pyodbc.Error as e:
            self.logger.error(f"Database error: {str(e)}")
        finally:
            if 'conn' in locals():
                conn.close()


    def find_insert_statement(self, sql_content: str, table_name: str) -> str:
        """
        Finds the exact INSERT INTO statement for a specified table in SQL content.
        
        Args:
            sql_content: The entire SQL script content
            table_name: The table name to search for (case-insensitive)
            
        Returns:
            The matched INSERT statement string, or None if not found
        """
        pattern = re.compile(
            rf'^\s*INSERT\s+INTO\s+{re.escape(table_name)}\b[^\x00]*?(?=(?:^s*INSERT\s+INTO\s+|\Z|^s*END))',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
            )
        
        match = pattern.search(sql_content)
        
        if match:
            start = match.start()
            end = sql_content.find(';', start) + 1  # To return full INSERT statement if it ends with a semicolon
            
            if end > start:
                return sql_content[start:end].strip()
            return match.group(0).strip()
        
        # If not found
        self.logger.warning(f"INSERT INTO statement for table '{table_name}' not found in SQL script")
        
        # Additional debug: Show all tables that do have INSERT statements
        all_inserts = re.findall(r'^\s*INSERT\s+INTO\s+(\w+)', sql_content, re.IGNORECASE | re.MULTILINE)
        if all_inserts:
            self.logger.debug(f"Tables with INSERT statements: {', '.join(set(all_inserts))}")
        
        return None
