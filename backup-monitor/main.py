# Copyright 2020 Merit International Inc. All Rights Reserved.

import os
import json
import time
import calendar

from googleapiclient.discovery import build
import pdpyras

"""
issue format:
{
    summary:
    severity:
    link:
    id:
}
"""

def get_backup_issues(gcloud_service, sql_instance, project):
    backup_link = f'https://console.cloud.google.com/sql/instances/{sql_instance}/backups?project={project}'
    issues = []
    # https://cloud.google.com/sql/docs/postgres/admin-api/rest/v1beta4/backupRuns/list
    req = gcloud_service.backupRuns().list(project=project, instance=sql_instance, maxResults=1)
    backup_list = req.execute()

    # These are basic sanity checks that should never fail.
    kind = backup_list.get('kind', None)
    backups = backup_list.get('items', [])
    if kind != 'sql#backupRunsList' or not backups:
        issues += [{
            'summary': 'There are no backups, or the backup API is inaccessible. This should never happen',
            'severity': 'critical',
            'link': backup_link
        }]
    else:
        backup = backups[0]
        backup_id = backup['id']

        # Check if this latest backup was successful, or if it's still in progress.
        # If we find no status field, make it fail
        status = backup.get('status', 'MERIT_NO_STATUS_FIELD_FOUND')
        if status not in ['ENQUEUED', 'RUNNING', 'SUCCESSFUL']:
            badbackup_id = f'badbackup{backup_id}'
            issues += [{
                'summary': f'The most recent backup is unsuccessful or inaccessible. Schedule a manual backup and determine the cause of failure in this backup.\n\nStatus: {status}\nBackupId: {backup_id}',
                'severity': 'warning',
                'link': backup_link,
                'id': badbackup_id
            }]
        
        # Check if this latest backup was more than 36 hours ago.
        now = calendar.timegm(time.gmtime())
        # If we find no startTime field, artificially make it really long ago...
        backup_time_field = backup.get('startTime', '1999-12-31T23:59:59.0Z')
        backup_start_time = calendar.timegm(time.strptime(backup_time_field, '%Y-%m-%dT%H:%M:%S.%fZ'))
        seconds_since_backup = now - backup_start_time
        if (seconds_since_backup/(60*60)) > 36:
            nobackup_id = f'nobackup{backup_id}'
            issues += [{
                'summary': f'There has not been a backup in over 36 hours. Schedule a manual backup and determine the cause of failure in automated backups.\n\nLast backup time: {backup_time_field}\nBackupId: {backup_id}',
                'severity': 'warning',
                'link': backup_link,
                'id': nobackup_id
            }]
    return issues

if __name__ == '__main__':
    local_env = {
        key: os.getenv(key) for key in [
            'PAGERDUTY_ROUTING_KEY',
            'PROJECT',
            'SQL_INSTANCES'
        ]
    }
    # Check that all of the expected environment variables exist
    early_exit = False
    for name, var in local_env.items():
        if not var:
            print(f'The environment variable "${name}" is missing. Please check the environment variable configuration executing this command.')
            early_exit = True

    if early_exit:
        exit(1)

    routing_key = local_env['PAGERDUTY_ROUTING_KEY']
    project = local_env['PROJECT']
    sql_instances = local_env['SQL_INSTANCES'].split(" ")

    # Construct the service object for the interacting with the Cloud SQL Admin API.
    # This will get the credentials from the local or GKE environment magically, 
    # which is how every Google SDK works. Magic auth...
    gcloud_service = build('sqladmin', 'v1beta4')

    issues = []

    for sql_instance in sql_instances:
        issues += get_backup_issues(
            gcloud_service=gcloud_service,
            sql_instance=sql_instance,
            project=project)

    if issues:
        pd_session = pdpyras.EventsAPISession(routing_key)
        for issue in issues:
            pd_session.trigger(summary = issue['summary'],
                               source = "GCP CloudSQL Backup",
                               severity = issue['severity'],
                               links = [{
                                   "href": issue['link'],
                                   "text": "Backup Monitor Alert"
                               }],
                               dedup_key = issue.get('id', None))
