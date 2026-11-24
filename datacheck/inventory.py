import csv
import io
import re
from collections import Counter

from datacheck.schemas import SCHEMAS


def analyze_dataset(csv_text: str, schema: dict) -> dict:
    id_field = schema['id_column']
    number_field = schema['numeric_column']
    category_field = schema['category_column']
    columns = (id_field, number_field, category_field)
    reader = csv.DictReader(io.StringIO(csv_text), strict=True)
    try:
        if reader.fieldnames != list(columns):
            raise ValueError(f'Expected columns: {", ".join(columns)}')
        rows = list(reader)
    except csv.Error as error:
        raise ValueError('Malformed CSV') from error
    if len(rows) > 1000:
        raise ValueError('Dataset exceeds the 1000-row safety limit')
    if any(None in row or any(row[field] is None for field in columns) for row in rows):
        raise ValueError('Dataset row has the wrong number of fields')
    if any(len(value) > 512 for row in rows for value in row.values()):
        raise ValueError('Dataset cell exceeds the 512-character safety limit')

    ids = Counter(row[id_field].strip() for row in rows)
    missing = dict.fromkeys(columns, 0)
    numbers = []
    issues = []

    for index, row in enumerate(rows, 1):
        def report(field, rule, explanation):
            issues.append({'rule_id': rule, 'row': index, 'column': field,
                           'observed_value': row[field], 'explanation': explanation})

        for field in columns:
            if not row[field].strip():
                missing[field] += 1
                report(field, 'required', 'A value is required.')
        identifier = row[id_field].strip()
        if identifier and ids[identifier] > 1:
            report(id_field, 'duplicate_id', 'This ID occurs more than once.')
        value = row[number_field].strip()
        if value:
            if not re.fullmatch(r'[+-]?[0-9]{1,12}', value):
                report(number_field, 'type', 'Value must be an integer of up to 12 digits.')
            else:
                number = int(value)
                numbers.append(number)
                upper = schema['maximum']
                if number < schema['minimum'] or (upper is not None and number > upper):
                    bounds = f"at least {schema['minimum']}" if upper is None else f"between {schema['minimum']} and {upper} inclusive"
                    report(number_field, 'range', f'Value must be {bounds}.')
        category = row[category_field].strip().lower()
        if category and category not in schema['categories']:
            report(category_field, 'category', f"Allowed values: {', '.join(schema['categories'])}.")

    summary = {'parsed_count': len(numbers), 'excluded_count': len(rows) - len(numbers),
               'min': min(numbers, default=None), 'max': max(numbers, default=None),
               'basis': 'All syntactically valid integers, including out-of-range values.'}
    return {'row_count': len(rows), 'columns': list(columns), 'missing_counts': missing,
            'numeric_summaries': {number_field: summary}, 'quantity_summary': summary,
            'issue_count': len(issues),
            'affected_row_count': len({issue['row'] for issue in issues}), 'issues': issues}


def analyze_inventory(csv_text: str) -> dict:
    """Compatibility entry point for the original inventory tests."""
    return analyze_dataset(csv_text, SCHEMAS['inventory'])
