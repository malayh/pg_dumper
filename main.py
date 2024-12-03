import logging
import time
import argparse
from pg_dumper.config import Config, Storage
from pg_dumper.backup import run_backup

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ProcessPoolExecutor

logging.basicConfig(format="[%(levelname)s]:%(name)s:%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO)
logger = logging.getLogger("pg_dumper")


def run_scheduler(config: Config):
    # TODO: Add a cleanp up job to remove old backups from working directory if exists
    # TODO: Remove old backups from S3. Keep only the latest 5 backups, or backups from the last 7 days
    logger.info("Starting scheduler")
    executors = {
        'default': ProcessPoolExecutor(2),
    }
    job_defaults = {
        'coalesce': False,
        'max_instances': 3
    }

    scheduler = BackgroundScheduler(executors=executors, job_defaults=job_defaults)

    for target in config.targets:
        logger.info(f"Scheduling job for {target.name} with schedule {target.schedule}")
        trigger = CronTrigger.from_crontab(target.schedule)
        scheduler.add_job(
            run_backup, 
            trigger=trigger, 
            args=[target, config],
        )

    scheduler.start()

    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped")
            

def main():
    parser = argparse.ArgumentParser(description="Backup PostgreSQL database to a S3")
    parser.add_argument("--config", type=str, help="Path to the config file",required=True)

    args = parser.parse_args()
    config = Config.from_config_file(args.config)
    logger.setLevel(logging.getLevelName(config.logLevel))
    run_scheduler(config)

if __name__ == "__main__":
    main()