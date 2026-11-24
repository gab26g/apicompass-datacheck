"""Render assessment monitoring/audit infrastructure; never calls AWS."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def ref(name):
    return {'Ref': name}


def sub(text):
    return {'Fn::Sub': text}


def render():
    resources = {
        'Alerts': {'Type': 'AWS::SNS::Topic', 'Properties': {
            'TopicName': 'apicompass-alerts',
            'Subscription': [{'Protocol': 'email', 'Endpoint': ref('AlertEmail')}],
            'Tags': [{'Key': 'Project', 'Value': 'APICompass'}]}},
        'AlertsPolicy': {'Type': 'AWS::SNS::TopicPolicy', 'Properties': {
            'Topics': [ref('Alerts')], 'PolicyDocument': {'Version': '2012-10-17', 'Statement': [{
                'Effect': 'Allow', 'Principal': {'Service': 'cloudwatch.amazonaws.com'},
                'Action': 'sns:Publish', 'Resource': ref('Alerts'), 'Condition': {
                    'StringEquals': {'aws:SourceAccount': ref('AWS::AccountId')},
                    'ArnLike': {'aws:SourceArn': sub('arn:${AWS::Partition}:cloudwatch:${AWS::Region}:${AWS::AccountId}:alarm:apicompass-*')}
                }}]}}},
        'AuditBucket': {'Type': 'AWS::S3::Bucket', 'DeletionPolicy': 'Retain', 'UpdateReplacePolicy': 'Retain', 'Properties': {
            'PublicAccessBlockConfiguration': dict.fromkeys(['BlockPublicAcls', 'BlockPublicPolicy', 'IgnorePublicAcls', 'RestrictPublicBuckets'], True),
            'OwnershipControls': {'Rules': [{'ObjectOwnership': 'BucketOwnerEnforced'}]},
            'VersioningConfiguration': {'Status': 'Enabled'},
            'BucketEncryption': {'ServerSideEncryptionConfiguration': [{'ServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]},
            'LifecycleConfiguration': {'Rules': [{'Id': 'FiniteAuditRetention', 'Status': 'Enabled', 'ExpirationInDays': 30, 'NoncurrentVersionExpiration': {'NoncurrentDays': 30}}]},
            'Tags': [{'Key': 'Project', 'Value': 'APICompass'}]}},
    }
    bucket_arn = {'Fn::GetAtt': ['AuditBucket', 'Arn']}
    trail_arn = sub('arn:${AWS::Partition}:cloudtrail:${AWS::Region}:${AWS::AccountId}:trail/apicompass-assessment')
    resources['AuditBucketPolicy'] = {'Type': 'AWS::S3::BucketPolicy', 'Properties': {
        'Bucket': ref('AuditBucket'), 'PolicyDocument': {'Version': '2012-10-17', 'Statement': [
            {'Effect': 'Deny', 'Principal': '*', 'Action': 's3:*', 'Resource': [bucket_arn, sub('${AuditBucket.Arn}/*')], 'Condition': {'Bool': {'aws:SecureTransport': 'false'}}},
            {'Effect': 'Allow', 'Principal': {'Service': 'cloudtrail.amazonaws.com'}, 'Action': 's3:GetBucketAcl', 'Resource': bucket_arn, 'Condition': {'StringEquals': {'aws:SourceArn': trail_arn}}},
            {'Effect': 'Allow', 'Principal': {'Service': 'cloudtrail.amazonaws.com'}, 'Action': 's3:PutObject',
             'Resource': sub('${AuditBucket.Arn}/AWSLogs/${AWS::AccountId}/*'), 'Condition': {'StringEquals': {'aws:SourceArn': trail_arn, 's3:x-amz-acl': 'bucket-owner-full-control'}}}
        ]}}}
    resources['AuditTrail'] = {'Type': 'AWS::CloudTrail::Trail', 'DependsOn': 'AuditBucketPolicy', 'Properties': {
        'TrailName': 'apicompass-assessment', 'S3BucketName': ref('AuditBucket'), 'IsLogging': True,
        'IsMultiRegionTrail': False, 'IncludeGlobalServiceEvents': True, 'EnableLogFileValidation': True,
        'EventSelectors': [{'ReadWriteType': 'All', 'IncludeManagementEvents': True}],
        'Tags': [{'Key': 'Project', 'Value': 'APICompass'}]}}
    project = [{'Name': 'Project', 'Value': 'APICompass'}]
    instance = [{'Name': 'InstanceId', 'Value': ref('InstanceId')}]
    # Missing custom telemetry is deliberately an alarm, not fabricated health.
    alarms = [
        ('Cpu', 'CPUUtilization', 'AWS/EC2', instance, 300, 2, 85, 'Average', 'notBreaching'),
        ('InstanceStatus', 'StatusCheckFailed', 'AWS/EC2', instance, 60, 1, 0, 'Maximum', 'notBreaching'),
        ('Disk', 'DiskUsedPercent', 'APICompass', project, 300, 2, 85, 'Maximum', 'breaching'),
        ('Health', 'HealthFailure', 'APICompass', project, 300, 1, 0, 'Maximum', 'breaching'),
        ('BackupFailure', 'BackupFailure', 'APICompass', project, 21600, 1, 0, 'Maximum', 'breaching'),
        ('AnswerFailure', 'AnswerFailure', 'APICompass', project, 300, 1, 0, 'Sum', 'breaching'),
    ]
    for name, metric, namespace, dims, period, evaluations, threshold, statistic, missing in alarms:
        resources[name + 'Alarm'] = {'Type': 'AWS::CloudWatch::Alarm', 'DependsOn': 'AlertsPolicy', 'Properties': {
            'AlarmName': 'apicompass-' + name.lower(), 'AlarmDescription': f'APICompass {metric}: inspect the operations runbook; missing telemetry policy={missing}.',
            'Namespace': namespace, 'MetricName': metric, 'Dimensions': dims,
            'Period': period, 'EvaluationPeriods': evaluations, 'DatapointsToAlarm': evaluations,
            'Threshold': threshold, 'ComparisonOperator': 'GreaterThanThreshold', 'Statistic': statistic,
            'TreatMissingData': missing, 'AlarmActions': [ref('Alerts')], 'OKActions': [ref('Alerts')]}}
    widgets = []
    for index, (_, metric, namespace, dims, period, _, _, statistic, _) in enumerate(alarms):
        dimension = ['InstanceId', '${InstanceId}'] if namespace == 'AWS/EC2' else ['Project', 'APICompass']
        widgets.append({'type': 'metric', 'x': (index % 2) * 12, 'y': (index // 2) * 6, 'width': 12, 'height': 6,
                        'properties': {'title': metric, 'region': '${AWS::Region}', 'view': 'timeSeries', 'period': period,
                                       'stat': statistic, 'metrics': [[namespace, metric, *dimension]]}})
    widgets.append({'type': 'metric', 'x': 0, 'y': 18, 'width': 24, 'height': 6,
                    'properties': {'title': 'Backup age (health fails above 8 hours)', 'region': '${AWS::Region}',
                                   'view': 'timeSeries', 'period': 300, 'stat': 'Maximum',
                                   'metrics': [['APICompass', 'BackupAgeHours', 'Project', 'APICompass']]}})
    widgets.append({'type': 'metric', 'x': 0, 'y': 24, 'width': 24, 'height': 6,
                    'properties': {'title': 'Synthetic API check duration (not full chat latency)', 'region': '${AWS::Region}',
                                   'view': 'timeSeries', 'period': 300, 'stat': 'Average',
                                   'metrics': [['APICompass', 'HealthLatencyMs', 'Project', 'APICompass']]}})
    widgets.append({'type': 'metric', 'x': 0, 'y': 30, 'width': 12, 'height': 6,
                    'properties': {'title': 'Questions attempted (request volume)', 'region': '${AWS::Region}',
                                   'view': 'timeSeries', 'period': 300, 'stat': 'Sum',
                                   'metrics': [
                                       ['APICompass', 'AnswerSuccess', 'Project', 'APICompass', {'id': 'success', 'visible': False}],
                                       ['APICompass', 'AnswerFailure', 'Project', 'APICompass', {'id': 'failure', 'visible': False}],
                                       [{'expression': 'success+failure', 'id': 'attempts', 'label': 'Question attempts'}]]}})
    widgets.append({'type': 'metric', 'x': 12, 'y': 30, 'width': 12, 'height': 6,
                    'properties': {'title': 'Observed question attempt duration', 'region': '${AWS::Region}',
                                   'view': 'timeSeries', 'period': 300, 'stat': 'Average',
                                   'metrics': [['APICompass', 'AnswerLatencyMs', 'Project', 'APICompass']]}})
    resources['Dashboard'] = {'Type': 'AWS::CloudWatch::Dashboard', 'Properties': {
        'DashboardName': 'APICompass-Operations', 'DashboardBody': sub(json.dumps({'widgets': widgets}, separators=(',', ':')))}}
    return {'AWSTemplateFormatVersion': '2010-09-09', 'Description': 'APICompass six email alarms, operations dashboard and single-region management-event audit trail.',
            'Parameters': {'InstanceId': {'Type': 'AWS::EC2::Instance::Id'}, 'AlertEmail': {'Type': 'String', 'NoEcho': True, 'AllowedPattern': '[^@\\s]+@[^@\\s]+\\.[^@\\s]+'}},
            'Resources': resources, 'Outputs': {'AlertsTopic': {'Value': ref('Alerts')}, 'AuditBucketName': {'Value': ref('AuditBucket')}}}


if __name__ == '__main__':
    (ROOT / 'infra/observability.json').write_text(json.dumps(render(), indent=2) + '\n', encoding='utf-8')
    print('Rendered infra/observability.json; no resources created.')
