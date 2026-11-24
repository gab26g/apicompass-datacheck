"""Calculate scores from reviewed real answers; this does not judge answers itself."""
import argparse
import json
from pathlib import Path
import sys


def summarize(document):
    mode = document.get('mode')
    if mode not in {'baseline', 'tool-grounded'}:
        raise ValueError('Mode must be baseline or tool-grounded')
    rows = document.get('cases')
    if not isinstance(rows, list):
        raise ValueError('Cases must be a list')
    seen, run, passed = set(), set(), []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Each case must be an object')
        case = row.get('id')
        if type(case) is not int or not 1 <= case <= 15:
            raise ValueError('Case IDs must be integers from 1 through 15')
        if case in seen:
            raise ValueError('Duplicate case ID')
        seen.add(case)
        if row.get('status') == 'not_run':
            continue
        if row.get('status') != 'run':
            raise ValueError('Case status must be run or not_run')
        if type(row.get('answer_supported')) is not bool:
            raise ValueError('answer_supported must be a boolean')
        if mode == 'tool-grounded' and type(row.get('tool_correct')) is not bool:
            raise ValueError('tool_correct must be a boolean')
        if not isinstance(row.get('evidence'), str) or not row['evidence'].strip():
            raise ValueError('Run cases require an evidence reference')
        run.add(case)
        if row['answer_supported'] and (mode == 'baseline' or row['tool_correct']):
            passed.append(case)
    return {'mode': mode, 'method': 'Arithmetic over reviewed outcomes; not automated answer adjudication',
            'passed': len(passed), 'run': len(run), 'planned': 15,
            'score': len(passed) / len(run) if run else None,
            'passed_cases': passed, 'run_cases': sorted(run),
            'not_run': sorted(set(range(1, 16)) - run)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    args = parser.parse_args()
    try:
        document = json.loads(args.input.read_text(encoding='utf-8'))
        if not isinstance(document, dict):
            raise ValueError('Input must be an object')
        result = summarize(document)
    except (OSError, ValueError) as error:
        print(f'Invalid evaluation input: {error}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
