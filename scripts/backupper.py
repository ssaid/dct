import subprocess
import os
import logging
import time

logging.basicConfig(level=logging.INFO, filename='/home/user/zeus/scripts/backup.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S')

_logger = logging.getLogger()
consoleH = logging.StreamHandler()
_logger.addHandler(consoleH)

odoo_dir = '/home/user/odoo/'
db_user = 'odoo'
db_name = 'prod'

dir_names = [name for name in os.listdir(odoo_dir) if os.path.isdir(os.path.join(odoo_dir, name))]

def sent_to_google_drive(dir_name):

    _logger.info(f"Sending backup {dir_name} to google drive...")

    command = f"/usr/bin/rclone copy /tmp/{dir_name} EynesDesarrollo:Zeus/{dir_name} -vvv"
    _logger.info(subprocess.run(command, shell=True, check=True))

    return 1

def mkdir(dir_name):

    backup_dir = f"/tmp/{dir_name}"

    try:
        _logger.info(f"Making dir {dir_name}")
        _logger.info(subprocess.run(f"/usr/bin/mkdir {backup_dir}", shell=True, check=True))
    except Exception as e:
        _logger.info(e)

    return backup_dir

for dir_name in dir_names:

    backup_dir = mkdir(dir_name)
    fs_backup_name = "fs.tgz"

    try:
        _logger.info("Backuping filestore...")
        fs_command = f"/usr/bin/docker run --rm --volumes-from {dir_name+'-odoo-1'} -v {backup_dir}:/backup-dir busybox tar cvf /backup-dir/{fs_backup_name} /var/lib/odoo/filestore/"

        _logger.info(subprocess.run(fs_command, shell=True, check=True))

    except Exception as e:
        _logger.info(e)

for dir_name in dir_names:

    backup_dir = mkdir(dir_name)
    db_backup_name = "db.sql.gz"

    try:

        _logger.info("Backuping database...")

        db_command = f"/usr/bin/docker exec {dir_name+'-db-1'} sh -c 'pg_dump -cU {db_user} {db_name}' | gzip > {backup_dir}/{db_backup_name}"

        container_status_command = subprocess.run(f"/usr/bin/docker inspect -f '{{{{.State.Status}}}}' {dir_name+'-db-1'}", shell=True, capture_output=True, text=True)
        _logger.info(container_status_command)

        if container_status_command.stdout.strip() != "running":

            _logger.error(f"{dir_name+'-db-1'} is not runnig")
            _logger.info(f"Strating {dir_name+'-db-1'}...")

            _logger.info(subprocess.run(f"/usr/bin/docker start {dir_name+'-db-1'}", shell=True, check=True))
            time.sleep(10)

            _logger.info(subprocess.run(db_command, shell=True, check=True))

            _logger.info(f'Backup {dir_name} success!')

            subprocess.run(f"/usr/bin/docker stop {dir_name+'-db-1'}", shell=True, check=True)
            _logger.info(f"Shutting down {dir_name}...")

            sent_to_google_drive(dir_name)

        else:

            _logger.info(subprocess.run(db_command, shell=True, check=True))
            _logger.info(f'Backup {dir_name} success!')
            sent_to_google_drive(dir_name)

        _logger.info(f"Removing dir: {dir_name}")

        subprocess.run(f"/usr/bin/rm -rf {backup_dir}", shell=True, check=True)

    except Exception as e:
        _logger.info(e)

_logger.info("Backup finished!")
