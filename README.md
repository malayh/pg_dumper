# pg_dumper
Tool for scheduling PostgreSQL backups to S3-compatible storage

# Usage

```bash
docker run malayh/pg_dumper:1.0.0 -d --name pg_dumper \
    -v pg_dumper_working_dir:/pg_dumper/backups \
    -v ./config.yaml:/pg_dumper/config.yaml \
```
- See [Configuration](#Configuration) for details on the configuration file
- See [docker-compose.yml](docker-compose.yml) for an example of how to run the tool with docker-compose

# Configuration

```yaml
workingDir: /pg_dumper/backups
logLevel: DEBUG
targets:
    # Name of the target. Must be unique across all targets
  - name: prod_appsmith
    # PostgreSQL connection details
    host: pg
    port: 5432
    username: postgres
    password: password
    database: db
    # How often to run the backup. Uses cron syntax
    schedule: "*/1 * * * *" 
    # Name of the storage to use. Must match a storage name in the storages section
    storage: pg_backup_prod
    # How long to keep backups for. Backups older than this will be deleted
    expireAfterDays: 7
    # How many backups will be kept even if they are older than expireAfterDays
    minRetention: 3
storages:
    # Name of the storage. Must be unique across all storages
  - name: pg_backup_prod
    # S3-compatible storage configurations
    endpoint: http://s3:9000
    accessKey: R5UNdUZCCfzXYAnQF50w
    secretKey: OEvK1F9B7GY29bHJJPtzRRKmHPruZ9Y5h0ULWf3n
    # Bucket name, must be created before running the tool
    bucket: pg-backup-prod

```