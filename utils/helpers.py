import os
import re
import logging
from typing import Pattern, List
from itertools import islice
import sqlparse
from config.constants import (
    FRAMEWORK_CONTAINERS,
    COMPONENT_PATTERNS
)


def validate_pattern(input_str: str, patterns: List[Pattern], logger: logging.Logger) -> bool:
    """Validate string against list of regex patterns."""
    for pattern in patterns:
        if pattern.match(input_str):
            logger.debug(f"Valid pattern match: {input_str}")
            return True
    logger.warning(f"Pattern validation failed for: {input_str}")
    return False


def clean_text(text: str) -> str:
    """Normalize and clean text for comparison."""
    return re.sub(r'(\s+|;|\bgo\b)', '', text.strip(), flags=re.IGNORECASE)


def compare_texts(text1: str, text2: str) -> float:
    """Calculate similarity percentage between two cleaned texts."""
    cleaned1 = clean_text(text1)
    cleaned2 = clean_text(text2)

    if not cleaned1 and not cleaned2:
        return 100.0

    max_len = max(len(cleaned1), len(cleaned2))
    matches = sum(1 for a, b in zip(cleaned1, cleaned2) if a == b)
    return round((matches / max_len) * 100, 2)


def validate_component_name(name: str, component_type: str, logger: logging.Logger) -> bool:
    """Validate component name against predefined patterns."""
    pattern = COMPONENT_PATTERNS.get(component_type)
    if not pattern:
        logger.error(f"Invalid component type: {component_type}")
        return False
    return bool(pattern.match(name))


def get_xpath(element, xpath: str, namespaces: dict):
    """Safe XPath value extraction with error handling."""
    result = element.xpath(xpath, namespaces=namespaces)
    return result[0] if result else None


def validate_container_structure(containers: List[str], logger: logging.Logger) -> bool:
    """Validate container names against framework requirements."""
    missing = []
    for pattern in FRAMEWORK_CONTAINERS:
        if not any(p.match(c) for c in containers for p in FRAMEWORK_CONTAINERS):
            missing.append(pattern.pattern)

    if missing:
        logger.warning(f"Missing containers matching patterns: {missing}")
        return False
    return True


def detect_package_type(package_name: str, logger: logging.Logger) -> str:
    """Detect if package is DIM or FACT based on naming convention."""
    if package_name.startswith('Fill_Dim'):
        logger.info("Detected DIMENSION package type")
        return 'DIM'
    elif package_name.startswith('Fill_Fact'):
        logger.info("Detected FACT package type")
        return 'FACT'
    else:
        logger.error("Invalid package naming convention")
        raise ValueError(
            "Package name must start with 'Fill_Dim' or 'Fill_Fact'")


def beautify_sql_query(
    sql_query: str,
    reindent: bool = False,
    reindent_aligned: bool = False,
    keyword_case: str = 'upper',
    strip_comments: bool = False,
    indent_columns: bool = True
) -> str:
    """Beautifies SQL scripts with batch separators and statement-specific formatting"""
    if not isinstance(sql_query, str) or not sql_query.strip():
        raise ValueError("The SQL query must be a non-empty string.")

    try:
        formatted = sqlparse.format(
            sql_query,
            reindent=reindent,
            reindent_aligned=reindent_aligned,
            keyword_case=keyword_case,
            strip_comments=strip_comments,
            indent_columns=indent_columns,
        )
    except Exception as e:
        raise RuntimeError(f"Error formatting statement: {e}")

    try:
        parsed = sqlparse.parse(formatted)
        if not parsed:
            return formatted

        output = []
        for statement in parsed:
            tokens = [t for t in statement.tokens if not t.is_whitespace]
            if not tokens:
                output.append(statement.value)
                continue

            # Conditions that determine which postprocessing is required
            condition1 = any((t1 == "CREATE" and t2 == "TABLE") for t1, t2 in zip(
                (tok1.value.upper() for tok1 in tokens),
                (tok2.value.upper() for tok2 in islice(tokens, 1, None))
            ))
            condition2 = any(tok.value.upper()=="UPDATE" for tok in tokens)
            condition3 = any(tok.value.upper()=="SELECT" for tok in tokens)

            # Apply statement-specific formatting
            if condition1:
                output.append(format_create_table(statement.value))
            elif condition2:
                output.append(align_equals_signs(statement.value))
            elif condition3:
                output.append(align_column_aliases(statement.value))
            else:
                output.append(statement.value)

        output = [query.strip('\n') for query in output]
        return '\n'.join(output)
    except Exception:
        return formatted


def format_create_table(sql: str) -> str:
    """Formats CREATE TABLE statements with aligned column definitions"""
    # Find the column definition block
    start_idx = sql.find('(')
    end_idx = sql.rfind(')')
    if start_idx == -1 or end_idx == -1:
        return sql
    
    prefix = sql[:start_idx+1]  # includes '('
    suffix = sql[end_idx:]       # includes ')' and anything after
    inner = sql[start_idx+1:end_idx]
    
    # Split column definitions while respecting inner parentheses
    columns = []
    depth = 0
    start = 0
    for i, char in enumerate(inner):
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char == ',' and depth == 0:
            col_def = inner[start:i].strip()
            if col_def:
                columns.append(col_def)
            start = i + 1
    # Add last column
    if last_col := inner[start:].strip():
        columns.append(last_col)
    
    if not columns:
        return prefix + " " + suffix    # Empty DDL

    # Extract column names and definitions
    col_data = []
    max_name_len = 0
    for col in columns:
        # Handle complex column names (quoted or bracketed)
        if match := re.match(r'^(\[[^\]]+\]|`[^`]+`|"[^"]+"|\w+)\s*(.*)', col, flags=re.DOTALL):
            col_name = match.group(1)
            rest = match.group(2).strip()
            col_data.append((col_name, rest))
            max_name_len = max(max_name_len, len(col_name))
    
    # Format columns with aligned definitions
    formatted_cols = []
    for i, (name, definition) in enumerate(col_data):
        comma = ',' if i < len(col_data) - 1 else ''
        formatted_cols.append(f"    {name.ljust(max_name_len)} {definition}{comma}")
    
    # Reassemble the SQL statement
    return f"{prefix}\n" + "\n".join(formatted_cols) + f"\n{suffix}"


def align_column_aliases(sql: str) -> str:
    """Aligns column aliases in SELECT statements while preserving other formatting"""
    lines = sql.split('\n')
    alias_lines = []
    
    # Find all lines with column aliases (AS keyword)
    for i, line in enumerate(lines):
        indent = line[:len(line) - len(line.lstrip())]
        stripped = line.strip()
        # Match patterns like: "column AS alias" or "expression) AS alias"
        match = re.search(r'\bAS\s+\w+(?=,|$)', stripped, re.IGNORECASE)
        if match:
            # Split into expression and alias parts
            as_start = match.start()
            expr = stripped[:as_start].strip()
            alias = stripped[as_start:].strip('AS').strip()
            alias_lines.append((i, indent, expr, alias))
    
    if not alias_lines:
        return sql
    
    # Find the maximum length of the expression part
    max_expr_length = max(len(expr) for (i, indent, expr, alias) in alias_lines)
    
    # Rebuild lines with aligned aliases
    for i, indent, expr, alias in alias_lines:
        lines[i] = f"{indent}{expr.ljust(max_expr_length)} AS {alias}"
    
    return '\n'.join(lines)


def align_equals_signs(sql: str) -> str:
    """Aligns equals signs in SQL assignment patterns using f-strings"""
    lines = sql.split('\n')
    assignment_lines = []
    
    # Find all lines with assignment patterns (column = value)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r'^\w+\s*=\s*\S+', stripped):
            # Split into left and right parts
            parts = stripped.split('=', 1)
            lhs = parts[0].strip()
            rhs = parts[1].strip()
            assignment_lines.append((i, lhs, rhs))
    
    if not assignment_lines:
        return sql
    
    # Find the maximum length of left-hand side (column names)
    max_lhs_length = max(len(lhs) for (i, lhs, rhs) in assignment_lines)
    
    # Rebuild lines with aligned equals signs
    for i, lhs, rhs in assignment_lines:
        lines[i] = f"    {lhs.ljust(max_lhs_length)} = {rhs}"
    
    return '\n'.join(lines)
