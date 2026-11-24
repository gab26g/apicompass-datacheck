"""Render the reviewed host bootstrap into a CloudFormation JSON artifact."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    template = json.loads((ROOT / 'infra/compute.base.json').read_text())
    bootstrap = (ROOT / 'infra/bootstrap-host.sh').read_text()
    template['Resources']['Host']['Properties']['UserData'] = {'Fn::Base64': {
        'Fn::Join': ['', ['#!/bin/bash\n', bootstrap]]}}
    output = ROOT / 'infra/compute.json'
    output.write_text(json.dumps(template, indent=2) + '\n', encoding='utf-8')
    print('Rendered infra/compute.json; no resources created.')
