"""Read fixed CSVs locally or from versioned private S3; never fall back silently."""
import hashlib
import json
import os
from pathlib import Path

from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from datacheck.schemas import SCHEMAS

DATA_DIR = Path(__file__).parent / 'data'
MAX_BYTES = 65536


def s3_client():
    import boto3
    # Default credential chain uses the instance role in AWS; no static keys here.
    return boto3.client('s3', config=Config(connect_timeout=2, read_timeout=3,
                                           retries={'mode': 'standard', 'total_max_attempts': 2}))


def read_dataset(dataset_id):
    if dataset_id not in SCHEMAS:
        raise ValueError('Unknown dataset')
    mode = os.environ.get('DATACHECK_STORAGE', 'local')
    if mode not in {'local', 's3'}:
        raise ValueError('Invalid storage mode')
    if os.environ.get('DATACHECK_ENV', 'local') != 'local' and mode != 's3':
        raise ValueError('Production requires S3-backed content')
    manifest = json.loads((DATA_DIR / 'manifest.json').read_text(encoding='utf-8'))
    try:
        expected_hash = manifest[dataset_id]['sha256']
    except (KeyError, TypeError) as error:
        raise ValueError('Invalid fixture manifest') from error
    object_version = None
    try:
        if mode == 'local':
            path = DATA_DIR / f'{dataset_id}.csv'
            if path.stat().st_size > MAX_BYTES:
                raise ValueError('Dataset exceeds byte limit')
            content = path.read_bytes()
        else:
            bucket = os.environ.get('DATACHECK_S3_BUCKET', '')
            if not bucket:
                raise ValueError('S3 bucket is not configured')
            response = s3_client().get_object(Bucket=bucket, Key=f'datasets/v2/{dataset_id}.csv')
            body = response['Body']
            try:
                if response['ContentLength'] > MAX_BYTES:
                    raise ValueError('Dataset exceeds byte limit')
                content = body.read(MAX_BYTES + 1)
                object_version = response.get('VersionId')
            finally:
                body.close()
            if not object_version or object_version == 'null':
                raise ValueError('S3 content must have a real object version')
        if len(content) > MAX_BYTES:
            raise ValueError('Dataset exceeds byte limit')
        digest = hashlib.sha256(content).hexdigest()
        if digest != expected_hash:
            raise ValueError('Dataset bytes do not match the declared fixture version')
        return content.decode('utf-8'), {'storage': mode, 'sha256': digest,
                                        'object_version': object_version}
    except (BotoCoreError, ClientError) as error:
        raise OSError('S3 content unavailable') from error
