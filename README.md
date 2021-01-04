Google CloudSQL Backup Monitor
---

This repository builds the docker container `cloudsql_backup_monitor` which can be used to alert you on PagerDuty if your SQL instance has not been backed-up in the last 24 hours. We use this at Merit to ensure SOC 2.0 compliance.

To use, simply run the docker container in a GCP environment with the following three environment variables set:

 - `PAGERDUTY_ROUTING_KEY`: The Integration Key to your PagerDuty service; not to be confused with an account API Token. See the [PagerDuty documentation](https://developer.pagerduty.com/docs/events-api-v2/trigger-events/) for more details
 - `PROJECT`: GCP Project which has the SQL Instances
 - `SQL_INSTANCES`: A space-separated list of SQL instances (MySQL or PostgreSQL) to be monitored

 A user or service account running this script will additionally require the following IAM permissions:
 - "cloudsql.backupRuns.get"
 - "cloudsql.backupRuns.list"
 - "resourcemanager.projects.get"
 - "serviceusage.services.get"
 - "serviceusage.services.list"