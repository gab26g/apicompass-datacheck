"""Export the four product operations; no credentials are read or exported."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datacheck.api import app

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--local', action='store_true', help='Remove bearer declarations for the private local-only stack.')
args = parser.parse_args()
schema = app.openapi()
if args.local:
    for path in schema['paths'].values():
        for operation in path.values():
            operation.pop('security', None)
    schema.get('components', {}).pop('securitySchemes', None)
print(json.dumps(schema, indent=2))
