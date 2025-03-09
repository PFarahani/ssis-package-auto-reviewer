import sys, os
import logging
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from lxml import etree
import yaml
import re


def resource_path(relative_path):
    """ Get the path to the resource, works for dev and for PyInstaller. """
    try:
        # PyInstaller temporary folder
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# Constants
LOG_FILENAME_FORMAT = 'PackageAutoReview_{timestamp}.log'
ICON_PATH = resource_path('favicon.ico')
SSIS_FILE_TYPES = [("SSIS Package files", "*.dtsx")]
SQL_FILE_TYPES = [("SQL files", "*.sql")]

PACKAGE_NAME_PATTERN = [r"^Fill_Dim\w+$"] # For dimension tables only
FRAMEWORK_CONTAINERS = [r"Stage.*Initialization",
                        r"Extract.*Transform.*OLTP",
                        r"Load.*Data",
                        r"Update.*Config.*Table.*Insert.*Log"]
PROPERTY_RULES = 'property_rules.yml'



class PackageAutoReview:
    def __init__(self):
        self.file_path = None
        self.sql_file_path = None
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = LOG_FILENAME_FORMAT.format(timestamp=self.timestamp)
        self.app = None  # Tkinter app window
        self.logging = self.configure_logging()

        self.query_dict = {} # A dictionary of SQL queries
        self.package_name = None
        self.elements = {}  # Package elements
        self.source_output_columns = {} # Data flow source component's output columns


    # def configure_logging(self):
    #     """Configure logging for the application."""
    #     logging.basicConfig(
    #         level=logging.DEBUG,
    #         format='%(asctime)s - %(levelname)s - %(message)s',
    #         filename=self.log_filename,
    #         filemode='w',
    #         force=True
    #     )
    #     return logging.getLogger()


    def configure_logging(self):
        """Configure logging for the application."""
        file_handler = logging.FileHandler(self.log_filename, mode='w')
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)

        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # Add both handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger




    def initialize_gui(self):
        """Initialize the Tkinter GUI for file selection."""
        self.app = tk.Tk()
        self.app.withdraw()
        self.app.iconbitmap(ICON_PATH)


    def get_file_path(self, dialog_title: str, filetypes):
        """Open file dialog to select a specific file."""
        return filedialog.askopenfilename(
            title=dialog_title,
            filetypes=filetypes
        )


    def process_sql(self):
        """Process the SQL file."""
        if self.sql_file_path:
            self.logging.info(f"Initiating query extraction from {self.sql_file_path}")            
            try:
                self.logging.info(f"Processing file: {self.sql_file_path}")
                with open(self.sql_file_path, 'r',  encoding='utf-8') as file:
                    sql_content = file.read()

                # Step 1: Check whether the correct SQL file is selected
                self.logging.info("Checking whether the SQL file name validity.")
                pattern = r'Table Name:\s*(\w+)'
                match = re.search(pattern, sql_content)
                if match:
                    table_name = match.group(1)  # Extract the table name
                    self.logging.info(f"Table Name: {table_name}")
                    # Check if the table name matches the expected name
                    expected_table_name = self.package_name.lstrip('Fill_')
                    if table_name != expected_table_name:
                        raise ValueError(f"Table name '{table_name}' does not match the expected '{expected_table_name}'.")
                    else:
                        self.logging.info("The relevant SQL file found.")
                else:
                    raise ValueError("Table name not found in the SQL file.")

                # Step 2: Extract and clean queries
                self.logging.info("Extracting all queries in the SQL file.")
                self.query_dict = self.extract_sql_sections(sql_content)
                if self.query_dict:
                    self.logging.info(f"{len(self.query_dict)} queries found.")
                    self.logging.info("Cleaning all query texts.")
                    self.query_dict = {key: self.clean_text(value) for key, value in self.query_dict.items()}

                else:
                    self.logging.warning(f"No queries found in the SQL file.")


            except Exception as e:
                self.logging.error(f"Unexpected error while processing {self.sql_file_path}: {e}")
                print(f"Unexpected error: {e}")
                input("Press ENTER to continue ...")
                sys.exit(1)

        else:
            self.logging.error("No file selected.")
            print("No file selected. Press ENTER to continue ...")
            sys.exit()


    def process_package(self):
        """Process the SSIS package file."""
        if self.file_path:
            self.logging.info(f"Initiating PackageAutoReview for {self.file_path}")            
            try:
                self.logging.info(f"Processing file: {self.file_path}")
                tree = etree.parse(self.file_path)
                root = tree.getroot()

                namespaces = {
                    'SQLTask': 'www.microsoft.com/sqlserver/dts/tasks/sqltask',
                    'DTS': 'www.microsoft.com/SqlServer/Dts'
                }
                # Step 1: Check the whole package and its SQL file 
                self.check_package(root, namespaces)
                self.process_sql()
                
                # Step 2: Check the "Stage Initialization" container
                self.logging.info("Reviewing \"Stage Initialization\" container.")
                self.process_stage_initialization(tree, namespaces)

                # Step 3: Load and prepare the rules from the YAML file
                self.logging.info("Loading the rules from the YAML file.")
                try:
                    property_rules = self.load_property_rules(PROPERTY_RULES)
                except:
                    self.logging.warning("Configuration file \'property_rules.yml\' not found. Creating the default configuration file...")
                    self.create_yaml_file(PROPERTY_RULES)
                    self.logging.info("The default configuration file \'property_rules.yml\' was created.")
                    property_rules = self.load_property_rules(PROPERTY_RULES)

                # Step 4: Review "Extract and Transform Data from OLTP" container
                self.logging.info("Reviewing \"Extract and Transform Data from OLTP\" container.")
                sqltask_patterns = [
                    r"^Create Clustered Index on \w+Stage$",
                    r"^Update IsExists$"
                ]
                self.process_oltp_extraction(tree, namespaces, property_rules, sqltask_patterns)

                # Step 5: Review "Load Data" container
                self.logging.info("Reviewing \"Load Data\" container.")
                sqltask_patterns = [
                    r"^Update \w+$"
                ]
                self.process_insert_to_warehouse(tree, namespaces, property_rules, sqltask_patterns)

                # Step 6: Review "Update Config Table & Insert Log" container
                self.logging.info("Reviewing \"Update Config Table & Insert Log\" container.")
                sqltask_patterns = [
                    r"^Insert PackageLog$"
                ]
                self.process_update_config_log(tree, namespaces, property_rules, sqltask_patterns)


            except etree.XMLSyntaxError as e:
                self.logging.error(f"Error parsing XML file {self.file_path}: {e}")
                print(f"Error parsing XML file: {e}")
                input("Press ENTER to continue ...")
                sys.exit(1)
            except Exception as e:
                self.logging.error(f"Unexpected error while processing {self.file_path}: {e}")
                print(f"Unexpected error: {e}")
                input("Press ENTER to continue ...")
                sys.exit(1)

        else:
            self.logging.error("No file selected.")
            print("No file selected. Press ENTER to continue ...")
            sys.exit()


    ###################################
    # Utilities
    ###################################
    def check_name(self, input_string, patterns):
        """
        This function checks if the input_string matches any of the provided patterns.

        :param pattern: The string to check.
        """
        match_found = False
        for pattern in patterns: 
            if bool(re.match(pattern, input_string)):
                match_found = True
                self.logging.info(f"\"{input_string}\" is a valid name.")
                break
        if not match_found:
            self.logging.warning(f'Invalid name found: \"{input_string}\"')


    def container_name_compliance(self, container_name, package_name):
        """
        This function checks whether the container name includes the package name.

        :param container_name: the container name
        :param package_name: the package name
        """
        name_pattern = package_name.lstrip('Fill_')
        if name_pattern not in container_name:
            self.logging.warning(f'Invalid name found: \"{container_name}\"\nThe container\'s name must include \"{name_pattern}\"')


    def create_yaml_file(self, filename):
        """
        Creates a YAML file with the given data if it does not exist.
        
        :param filename: The .yml file name
        """
        # YAML Comments to Insert
        comments = """
        # Dataflow Component Properties Rules
        # 
        # This YAML file contains the validation rules for various components of the dataflow pipeline.
        # Each component has its own set of properties that need to be validated according to predefined conditions.
        #
        # Structure:
        # - Each rule set corresponds to a specific component type (e.g., 'oledb_source', 'oracle_source').
        # - Each rule set contains a list of property rules.
        # - Each property rule specifies:
        #   - `condition`: The validation method to apply (e.g., 'equals', 'str_not_empty', 'is_none', 'regex_match').
        #   - `value`: The value or pattern used for validation (if applicable).
        #     - For conditions like 'equals', `value` is the expected value.
        #     - For conditions like 'regex_match', `value` is the regex pattern.
        # 
        # Example:
        # - A property rule could validate if a property value is a non-empty string, or if it matches a specific pattern.
        #
        # Adding New Rules:
        # - To add a new rule for a property, define the `condition` and `value` (if needed) in the relevant section.
        # - To add a new condition, define the validation function in the Python code and map it in the `validation_functions` dictionary.
        """
        # Predefined property rules
        data = {
            'oledb_source': {
                'AlwaysUseDefaultCodePage': {'condition': 'equals', 'value': 'false'},
                'DefaultCodePage': {'condition': 'equals', 'value': '1252'},
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
                'DefaultCodePage': {'condition': 'equals', 'value': '1256'},
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

        if not os.path.exists(filename):
            with open(filename, 'w') as file:
                file.write(comments.strip() + "\n\n")
                yaml.dump(data, file, default_flow_style=False)
        else:
            print(f"{filename} already exists.")


    def load_property_rules(self, yaml_file):
        """Load YAML and map conditions to corresponding validation functions"""
        # Validation Functions

        def validate_equals(value, expected):
            """Check if the value is equal to the expected value."""
            return value == expected

        def validate_str_not_empty(value):
            """Check if the value is a non-empty string."""
            return isinstance(value, str) and value != ''

        def validate_is_none(value):
            """Check if the value is None."""
            return value is None

        def validate_regex(value, pattern):
            """Check if the value matches the regex pattern."""
            return bool(re.match(pattern, value))

        # Validation Function Mapping
        validation_functions = {
            'equals': validate_equals,
            'str_not_empty': validate_str_not_empty,
            'is_none': validate_is_none,
            'regex_match': validate_regex,
        }

        with open(yaml_file, 'r') as file:
            property_rules = yaml.load(file, Loader=yaml.FullLoader)
        
        # Parse and map the conditions from YAML to actual functions
        for rule_set in property_rules.values():
            for key, rule in rule_set.items():
                condition = rule.get('condition')
                value = rule.get('value')
                
                # Map the condition to the corresponding function
                validate_func = validation_functions.get(condition)
                if validate_func:
                    # If the validation function requires a value, pass it
                    rule_set[key] = (validate_func, value) if value is not None else (validate_func,)
                else:
                    self.logging.warning(f"No validation function found for condition: {condition}")
        
        return property_rules


    def extract_sql_sections(self, file_content):
        """
        This function extracts the queries from the SQL file, given the specific
        patterns that separates each query.
        The output is a dictionary of section name and the query within.
        """
        # Split the content into sections based on the delimiter
        delimiter_pattern = r'\-\-\-+\n'
        sections = re.split(delimiter_pattern, file_content)
        section_dict = {}
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            # Extract the section name, which comes right after '--' comment
            match = re.match(r'--(.*?)(\n|$)', section)
            if match:
                section_name = match.group(1).strip()  # The section name
                query = section[len(match.group(0)):].strip()  # The query part
                
                # Regex pattern to match and remove the USE statements
                pattern = r'(?i)^\s*USE\s+.*\s*;?\s*(\n|$)'
                cleaned_query = re.sub(pattern, '', query, flags=re.MULTILINE)

                section_dict[section_name] = cleaned_query
        
        return section_dict


    def clean_text(self, text):
        """
        This function removes unnecessary whitespaces, newlines, tabs, and 
        other formatting issues from the given text.
        """
        cleaned_text = re.sub(r'(\s+|;|\bgo\b)', '', text.strip(), flags=re.IGNORECASE)
        return cleaned_text


    def compare_texts(self, text1, text2):
        """
        Compares two texts by cleaning them and returning the percentage of similarity.
        """
        cleaned_text1 = self.clean_text(text1)
        cleaned_text2 = self.clean_text(text2)

        matches = sum(1 for a, b in zip(cleaned_text1, cleaned_text2) if a == b)
        total = max(len(cleaned_text1), len(cleaned_text2))
        
        return (matches / total) * 100 if total > 0 else 100


    ###################################
    # Container Processing Functions
    ###################################
    def check_package(self, root, namespaces):
        """
        Check the whole SSIS package for various components such as package name,
        available containers, variables, and package parameters.
        
        :param root: The root element of the parsed SSIS package XML.
        :param namespaces: The namespaces dictionary for XPath queries.
        """
        # Step 1: Check the package name
        self.package_name = root.xpath('@DTS:ObjectName', namespaces=namespaces)[0]
        self.logging.info("Checking package name.")
        self.check_name(self.package_name, PACKAGE_NAME_PATTERN)

        # Step 2: Retrieve all available components (executables)
        self.logging.info("Retrieving all available components.")
        self.elements = {}
        for element in root.find('.//DTS:Executables', namespaces).findall('.//DTS:Executable', namespaces):
            path = element.getroottree().getelementpath(element)
            attrib_dict = dict(name=element.xpath('@DTS:ObjectName', namespaces=namespaces)[0],
                            type=element.xpath('@DTS:ExecutableType', namespaces=namespaces)[0])
            self.elements[path] = attrib_dict

        # Step 3: Retrieve all available containers
        self.logging.info("Retrieving all available containers.")
        containers = [root.find(c).xpath('@DTS:ObjectName', namespaces=namespaces)[0] for c in self.elements.keys() if root.find(c).xpath('@DTS:ExecutableType', namespaces=namespaces)[0] == "STOCK:SEQUENCE"]
        containers = set(containers)

        # Step 4: Compare containers with the framework containers
        self.logging.info(f"Available containers: {containers}")
        missing_elements = [c for c in containers if not any(re.match(pattern, c) for pattern in FRAMEWORK_CONTAINERS)]
        if missing_elements:
            self.logging.warning(f"Missing/Extra container(s): {missing_elements}")
        if not missing_elements:
            self.logging.info("All framework containers are available.")

        # Step 5: Check if Variables exist
        self.logging.info(f"Checking if Variables exist.")
        try:
            variables = root.xpath('.//@DTS:Variables', namespaces)[0]
            if len(variables) > 0:
                self.logging.warning(f"{len(variables)} Variables found!")
        except Exception as e:
            self.logging.info("No Variables found.")

        # Step 6: Check if PackageParameters exist
        self.logging.info(f"Checking if PackageParameters exist.")
        try:
            package_parameters = root.xpath('.//@DTS:PackageParameters', namespaces)[0]
            if len(package_parameters) > 0:
                self.logging.warning(f"{len(package_parameters)} PackageParameters found!")
        except Exception as e:
            self.logging.info("No PackageParameters found.")


    def process_stage_initialization(self, tree, namespaces):
        """
        This function processes the \"Stage Initialization\" container.
        
        :param tree: The parsed XML tree.
        :param namespaces: The namespaces dictionary for XPath queries.
        """
        try:
            found = False
            for key, value in self.elements.items():
                if re.match(r"Stage.*Initialization", value['name']):
                    # Compare SQL queries
                    self.logging.info("Comparing Stage Initialization queries.")
                    query1 = tree.find(key).find('.//SQLTask:SqlTaskData', namespaces).xpath('@SQLTask:SqlStatementSource', namespaces=namespaces)[0]
                    query2 = self.query_dict['Stage Initialization']
                    similarity_percentage = self.compare_texts(query1, query2)
                    
                    if similarity_percentage==100:
                        self.logging.info(f"The queries are identical.")
                    else:
                        self.logging.warning(f"The queries are {similarity_percentage:.2f}% similar.")
                    
                    found = True 
                    break
            if not found:
                raise ValueError("\"Stage Initialization\" not found in elements.")

        except ValueError as e:
            logging.warning(e)


    def process_oltp_extraction(self, tree, namespaces, property_rules, sqltask_patterns):
        """
        This function processes the \"Extract and Transform Data from OLTP\" container.
        
        :param tree: The parsed XML tree.
        :param namespaces: The namespaces dictionary for XPath queries.
        :param property_rules: A dictionary of all property rules.
        :param sqltask_patterns: A dictionary of all SQLTask patterns within the container.
        """
        try:
            found = False
            for key, value in self.elements.items():
                if re.match(r"Extract.*Transform.*OLTP", value['name']):

                    # Check ExecuteSQLTask component names within the container
                    for c in tree.find(key).find('DTS:Executables', namespaces=namespaces):
                        
                        # Review component details
                        if c.xpath('@DTS:ExecutableType', namespaces=namespaces)[0] == "Microsoft.Pipeline":
                            pipeline_element = c.find('.//pipeline')
                            # Call dataflow review function
                            self.dataflow_review(pipeline_element, property_rules)
                        
                        # Review CLUSTERED INDEX & IsExists components
                        elif c.xpath('@DTS:ExecutableType', namespaces=namespaces)[0] == "Microsoft.ExecuteSQLTask":
                            
                            self.check_name(c.xpath('@DTS:ObjectName', namespaces=namespaces)[0], sqltask_patterns)
                            
                            # Check CLUSTERED INDEX query
                            if re.match(sqltask_patterns[0], c.xpath('@DTS:ObjectName', namespaces=namespaces)[0]):
                                # Compare SQL queries
                                self.logging.info("Comparing CLUSTERED INDEX creation queries.")
                                table_name = self.package_name.lstrip('Fill_')
                                query1 = c.find('.//SQLTask:SqlTaskData', namespaces).xpath('@SQLTask:SqlStatementSource', namespaces=namespaces)[0]
                                query2 = self.query_dict[f'Create Clustered Index on {table_name}Stage']
                                similarity_percentage = self.compare_texts(query1, query2)
                                
                                if similarity_percentage==100:
                                    self.logging.info(f"The queries are identical.")
                                else:
                                    self.logging.warning(f"The queries are {similarity_percentage:.2f}% similar.")
                        
                            # Check IsExists query
                            elif re.match(sqltask_patterns[1], c.xpath('@DTS:ObjectName', namespaces=namespaces)[0]):
                                # Compare SQL queries
                                self.logging.info("Comparing IsExists queries.")
                                query1 = c.find('.//SQLTask:SqlTaskData', namespaces).xpath('@SQLTask:SqlStatementSource', namespaces=namespaces)[0]
                                query2 = self.query_dict['Update IsExists']
                                similarity_percentage = self.compare_texts(query1, query2)
                                
                                if similarity_percentage==100:
                                    self.logging.info(f"The queries are identical.")
                                else:
                                    self.logging.warning(f"The queries are {similarity_percentage:.2f}% similar.")

                found = True 
                break
            if not found:
                raise ValueError("\"Stage Initialization\" not found in elements.")

        except ValueError as e:
            self.logging.warning(e)


    def process_insert_to_warehouse(self, tree, namespaces, property_rules, sqltask_patterns):
        """
        This function processes the \"Load Data\" container.
        
        :param tree: The parsed XML tree.
        :param namespaces: The namespaces dictionary for XPath queries.
        :param property_rules: A dictionary of all property rules.
        :param sqltask_patterns: A dictionary of all SQLTask patterns within the container.
        """
        try:
            found = False
            for key, value in self.elements.items():
                if re.match(r"Load.*Data", value['name']):
                    
                    # Check ExecuteSQLTask component names within the container
                    for c in tree.find(key).find('DTS:Executables', namespaces=namespaces):
                        
                        # Review component details
                        if c.xpath('@DTS:ExecutableType', namespaces=namespaces)[0] == "Microsoft.Pipeline":
                            pipeline_element = c.find('.//pipeline')

                            # Update the 'DefaultCodePage' for 'oledb_destination'
                            property_rules['oledb_destination']['DefaultCodePage'] = (lambda x: x == '1252',)

                            # Call dataflow review function
                            self.dataflow_review(pipeline_element, property_rules)
                        
                        # Review CLUSTERED INDEX & IsExists components
                        elif c.xpath('@DTS:ExecutableType', namespaces=namespaces)[0] == "Microsoft.ExecuteSQLTask":
                            
                            self.container_name_compliance(c.xpath('@DTS:ObjectName', namespaces=namespaces)[0], self.package_name)

                            # Check UPDATE query
                            if re.match(sqltask_patterns[0], c.xpath('@DTS:ObjectName', namespaces=namespaces)[0]):
                                # Compare SQL queries
                                self.logging.info("Comparing UPDATE queries.")
                                table_name = self.package_name.lstrip('Fill_')
                                query1 = c.find('.//SQLTask:SqlTaskData', namespaces).xpath('@SQLTask:SqlStatementSource', namespaces=namespaces)[0]
                                query2 = self.query_dict[f'Update {table_name}']
                                similarity_percentage = self.compare_texts(query1, query2)
                                
                                if similarity_percentage==100:
                                    self.logging.info(f"The queries are identical.")
                                else:
                                    self.logging.warning(f"The queries are {similarity_percentage:.2f}% similar.")

                    found = True 
                    break
            if not found:
                raise ValueError("\"Load Data\" not found in elements.")

        except ValueError as e:
            self.logging.warning(e)


    def process_update_config_log(self, tree, namespaces, property_rules, sqltask_patterns):
        """
        This function processes the \"Update Config Table & Insert Log\" container.
        
        :param tree: The parsed XML tree.
        :param namespaces: The namespaces dictionary for XPath queries.
        :param property_rules: A dictionary of all property rules.
        :param sqltask_patterns: A dictionary of all SQLTask patterns within the container.
        """
        try:
            found = False
            for key, value in self.elements.items():
                if re.match(r"Update.*Config.*Table.*Insert.*Log", value['name']):
                    
                    # Check ExecuteSQLTask component names within the container
                    for c in tree.find(key).find('DTS:Executables', namespaces=namespaces):
                        
                        # Review INSERT PACKAGE LOG component
                        if c.xpath('@DTS:ExecutableType', namespaces=namespaces)[0] == "Microsoft.ExecuteSQLTask":
                            
                            self.container_name_compliance(c.xpath('@DTS:ObjectName', namespaces=namespaces)[0], 'Insert PackageLog')

                            # Check INSERT PACKAGE LOG query
                            if re.match(sqltask_patterns[0], c.xpath('@DTS:ObjectName', namespaces=namespaces)[0]):
                                # Compare SQL queries
                                self.logging.info("Comparing INSERT PACKAGE LOG queries.")
                                query1 = c.find('.//SQLTask:SqlTaskData', namespaces).xpath('@SQLTask:SqlStatementSource', namespaces=namespaces)[0]
                                query2 = self.query_dict['Insert PackageLog']
                                similarity_percentage = self.compare_texts(query1, query2)
                                
                                if similarity_percentage==100:
                                    self.logging.info(f"The queries are identical.")
                                else:
                                    self.logging.warning(f"The queries are {similarity_percentage:.2f}% similar.")

                    found = True 
                    break
            if not found:
                raise ValueError("\"Update Config Table & Insert Log\" not found in elements.")

        except ValueError as e:
            self.logging.warning(e)


    ###################################
    # dataflow_review Helper Functions
    ###################################
    def check_compliance(self, input_properties, rules):
        """
        Check if the input properties comply with the defined rules.
        
        :param input_properties: A dictionary containing the component properties to check.
        :param rules: A dictionary where each key corresponds to a property name,
                    and the value is a function to check the corresponding value.
        """
        for rule_key, (validate_func, *args) in rules.items():
            value = input_properties.get(rule_key)
            if value is not None:
                if not validate_func(value, *args):
                    self.logging.warning(f"Warning: '{rule_key}' failed validation. Found value: {value}")
            else:
                if rule_key in ('FastLoadOptions', 'SqlCommand', 'SqlCommandVariable'):
                    self.logging.info(f"'{rule_key}' is blank in the component properties.")
                else:
                    self.logging.warning(f"'{rule_key}' is missing in the component properties.")


    def review_component(self, component, component_rules, patterns, output_columns_func=None):
        """
        Common logic for reviewing a component, including name checks, properties checks,
        and output column checks.
        
        :param component: The component XML element to review
        :param component_rules: Rules for reviewing component properties
        :param patterns: Patterns for name compliance
        :param output_columns_func: A function to handle output column checks
        """
        self.logging.info(f'Reviewing "{component.attrib["componentClassID"]}" component.')

        self.check_name(component.attrib['name'], patterns=patterns)

        # Check component properties for compliance
        properties = {p.attrib['name']: p.text for p in component.findall('.//property')}
        self.check_compliance(properties, component_rules)

        # Handle output columns if applicable
        if output_columns_func:
            self.source_output_columns = output_columns_func(component)


    def check_unmatched_columns(self, component, source_output_columns):
        """
        Check for unmatched columns between input and external metadata columns in OLEDBDestination.
        
        :param component: The component XML element to review
        :param source_output_columns: Output columns of the source component
        """
        inputs = {p.attrib['cachedName']: p.attrib['cachedDataType'] for p in component.findall('.//inputColumn')}
        external_metadata_columns = {p.attrib['name']: p.attrib['dataType'] for p in component.findall('.//externalMetadataColumn')}
        
        # Sets for case-insensitive comparison
        inputs_lower = {key.lower() for key in inputs}
        external_metadata_columns_lower = {key.lower() for key in external_metadata_columns}

        difference_lower = external_metadata_columns_lower - inputs_lower

        # unmatched_columns = set(external_metadata_columns.keys()) - set(inputs.keys())
        unmatched_columns = [key for key in external_metadata_columns if key.lower() in difference_lower]

        if unmatched_columns:
            self.logging.warning("Unmatched column(s) found in \"%s\" component:\n%s", component.attrib['name'], unmatched_columns)


    def check_unselected_columns(self, component, source_output_columns):
        """
        Check for unselected columns in MultipleHash component.
        
        :param component: The component XML element to review
        :param source_output_columns: Output columns of the source component
        """
        inputs = {p.attrib['cachedName']: p.attrib['cachedDataType'] for p in component.findall('.//inputColumn')}
        
        unselected_columns = set(source_output_columns.keys()) - set(inputs.keys())
        if unselected_columns:
            self.logging.warning("Unselected column(s) found in \"%s\" component:\n%s", component.attrib['name'], unselected_columns
            )


    def dataflow_review(self, pipeline_element, property_rules: dict):
        """
        The purpose of this function is to review the DataFlow task in the pipeline.
        It checks component properties, naming conventions, and specific attributes
        to ensure compliance with predefined rules.
        
        :param pipeline_element: The pipeline XML element representing the dataflow
        :param property_rules: A dictionary of all property rules
        """
        # Step 1: Check AutoAdjustBufferSize and other attributes
        self.logging.info("Checking AutoAdjustBufferSize property.")
        if pipeline_element.attrib.get('autoAdjustBufferSize', None) is None:
            self.logging.warning("The 'AutoAdjustBufferSize' attribute is False.")
        else:
            self.logging.info("'AutoAdjustBufferSize' is checked.")
        # Log other DataFlow custom attributes
        self.logging.info('Other data flow custom attributes:\n%s', {
            key: value for key, value in pipeline_element.attrib.items() if key not in ['version', 'autoAdjustBufferSize']
        })

        # Step 2: Review components 
        # Review components within the DataFlow
        self.logging.info("Retrieving all available components within the data flow.")
        components = pipeline_element.find('.//components')
        
        # Step 3: Review all components
        # Initialize source_output_columns variable
        source_output_columns = {}

        for component in components:
            component_class_id = component.attrib['componentClassID']

            if component_class_id == 'Microsoft.OLEDBSource':
                self.review_component(component, property_rules['oledb_source'], 
                                patterns=[r'^Get Data [Ff]rom \w+$'], 
                                output_columns_func=lambda comp: {
                                    p.attrib['name']: p.attrib['dataType']
                                    for p in comp.findall('.//output[@name="OLE DB Source Output"]/outputColumns/outputColumn')
                                })
                
            elif component_class_id == 'Microsoft.SSISOracleSrc':
                self.review_component(component, property_rules['oracle_source'], 
                                patterns=[r'^Get Data [Ff]rom \w+$'], 
                                output_columns_func=lambda comp: {
                                    p.attrib['name']: p.attrib['dataType']
                                    for p in comp.findall('.//output[@name="Oracle Source Output"]/outputColumns/outputColumn')
                                })

            elif component_class_id == 'Microsoft.OLEDBDestination':
                name_pattern = [r'^Insert [Ii]nto ' + self.package_name.lstrip('Fill_') + r'\w*\s?\w+$']

                self.review_component(component, property_rules['oledb_destination'], 
                                patterns=name_pattern)
                
                self.check_unmatched_columns(component, self.source_output_columns)

            elif component_class_id == 'Microsoft.ManagedComponentHost' and component.attrib.get('contactInfo') == 'https://github.com/keif888/SSISMHash/':
                self.review_component(component, property_rules['multiple_hash'], 
                                patterns=[r'^Multiple Hash'])
                self.check_unselected_columns(component, self.source_output_columns)

        # Final log to indicate completion
        self.logging.info("Data flow review completed.")


    ###################################
    # Main
    ###################################
    def main(self):
        """Main method to run the application logic."""
        self.initialize_gui()  # Initialize GUI
        self.file_path = self.get_file_path(dialog_title="Select SSIS Package", filetypes=SSIS_FILE_TYPES)
        self.sql_file_path = self.get_file_path(dialog_title="Select SQL File", filetypes=SQL_FILE_TYPES)
        self.process_package()  # Process the file
        print("Finished package auto review.")
        input("Press ENTER to continue ...")


if __name__ == '__main__':
    app = PackageAutoReview()
    app.main()