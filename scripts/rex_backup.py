#!/usr/bin/env python
"""
    Copyright 2013 CRX Markets S.A.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
__author__ = "Denys Sobchyshak"
__email__ = "denys.sobchyshak@gmail.com"
__version__ = 1.1

import logging
import datetime
import time
import smtplib
import operator
import socket
import os
import re
from email.mime.text import MIMEText
from optparse import OptionParser

import fileutils
import config


class Status:
    Success = "SUCCESS"
    Incomplete = "INCOMPLETE"
    Skipped = "SKIPPED"
    Failed = "FAILED"


class Messages:
    Success = "Successfully performed %(what)s on %(where)s."
    Skipped = "Skipped %(what)s on %(where)s."
    Failed = "Failed to perform %(what)s on %(where)s."


class Tasks:
    Backup = "backup task"
    Check = "backup check task"
    Cleanup = "cleanup task"


ARCHIVE_FORMATS = ["zip", "tar", "bztar", "gztar"]
messages = []
status = Status.Success
skipped_backups = 0
inconsistencies_found = 0


#-----------------------------------------------------------------------------------------------------------------------
# General functions
#-----------------------------------------------------------------------------------------------------------------------
def get_global_status():
    """
    Parses global status and messages and determines real status of a backup.
    """
    global status
    failedMessages = []
    if status == Status.Skipped:
        return status
    for m in messages:
        if m.startswith(Status.Failed):
            failedMessages.append(m)
            status = Status.Incomplete

    for m in failedMessages:
        if Tasks.Backup in m:
            status = Status.Failed

    return status


def add_message(status, task_type, location, message=""):
    """
    Adds provided info to the messages.
    """
    global messages
    template = get_template_by_status(status)
    messages.append(status + ": " + (template % {"what": task_type, "where": location}) + "\n" + message)


def get_template_by_status(status):
    """
    Parses status and return corresponding template
    """
    if status == Status.Success:
        return Messages.Success
    elif status == Status.Skipped:
        return Messages.Skipped
    elif status == Status.Failed:
        return Messages.Failed


#-----------------------------------------------------------------------------------------------------------------------
# Main tasks and routines
#-----------------------------------------------------------------------------------------------------------------------
def main():
    global status, skipped_backups, inconsistencies_found
    #Processing configuration
    rex_config = None
    try:
        config_file_path = os.path.join(fileutils.get_working_dir(), "resources", "config.xml")
        logging.info("Reading config file: " + config_file_path)
        rex_config = config.readConfig(config_file_path)
    except Exception as ex:
        logging.fatal("Failed to parse configuration file. Reason: " + ex.__str__())

    if rex_config:
        #step 1:performing backups
        if len(rex_config.backups) > 0:
            for backup in rex_config.backups:
                if not is_downtime_period(backup):
                    try:
                        perform_backup(backup)
                        add_message(Status.Success, Tasks.Backup, backup.source)
                    except Exception as ex:
                        add_message(Status.Failed, Tasks.Backup,backup.source,ex.__str__())
                        logging.error("Failed to perform backup: " + ex.__str__())
                        break
                    try:
                        if rex_config.performChecks:
                            perform_backup_check(backup)
                            add_message(Status.Success, Tasks.Check, backup.source)
                    except ArchiveIntegrityError as ex:
                        add_message(Status.Failed, Tasks.Check,backup.source,ex.__str__())
                        logging.error("Backup check found some archive inconsistencies: " + ex.__str__())
                        inconsistencies_found+=len(ex.inconsistencies)
                    except Exception as ex:
                        add_message(Status.Failed, Tasks.Check,backup.source,ex.__str__())
                        logging.error("Failed to perform backup check: " + ex.__str__())
                else:
                    skipped_backups += 1
                    add_message(Status.Skipped, Tasks.Backup, backup.source)
                fileutils.clean_tmp()
            if skipped_backups == len(rex_config.backups):
                status = Status.Skipped

        #step 2:performing cleanup
        try:
            perform_backup_cleanup(rex_config)
            add_message(Status.Success, Tasks.Cleanup, fileutils.get_tmp_dir())
        except Exception as ex:
            add_message(Status.Failed, Tasks.Cleanup, fileutils.get_tmp_dir(), ex.__str__())
            logging.error("Failed to perform backup cleanup: " + ex.__str__())

        #step 3: performing reporting
        try:
            if rex_config.performReporting:
                perform_reporting(messages, rex_config.reporterConfig)
        except Exception as ex:
            logging.error("Failed to perform reporting: " + ex.__str__())


def is_downtime_period(backup_config):
    if int(backup_config.backupDowntime) == 0:
        return False
    else:
        archive_path = get_newest_archive_path(backup_config.target)
        if archive_path:
            last_backup_time = parse_archive_date(archive_path).date()
            next_backup_time = last_backup_time + datetime.timedelta(days=int(backup_config.backupDowntime))
            now = datetime.date.fromtimestamp(time.time())
            if now < next_backup_time:
                return True
        else:
            return False


def perform_backup(backup_config):
    """
    Performs backup according to provided config.
    """
    try:
        logging.info("Performing backup task: " + backup_config.__str__())

        logging.info("Archiving directory: " + backup_config.source)
        archive_file_path = fileutils.archive_dir(backup_config.source, ARCHIVE_FORMATS[3])
        logging.info("Copying archive to target directory: " + backup_config.target)
        fileutils.copy_file(archive_file_path, backup_config.target)

        logging.info("Backup complete")
    except Exception as ex:
        raise TaskError("Failed to perform backup: " + ex.__str__())


def perform_backup_check(backup_config):
    """
    Checks if backup was performed correctly according to specified config.
    """
    try:
        logging.info("Checking backup: " + backup_config.__str__())

        archive_path = get_newest_archive_path(backup_config.target)
        if not archive_path:
            raise TaskError("No archive was found in the target dir: " + backup_config.target)
        logging.info("Copying newest archive: " + archive_path)
        tmp_archive = fileutils.copy_file(archive_path, fileutils.get_tmp_remote_dir())
        logging.info("Checking archive consistency.")
        inconsistencies = fileutils.compare_archive_against_dir(tmp_archive, backup_config.source, backup_config.excludeRegexp)

        logging.info("Backup check completed")
        if inconsistencies:
            raise ArchiveIntegrityError("Found inconsistencies while checking archive and source.", inconsistencies)
    except ArchiveIntegrityError as ex:
        raise ex
    except Exception as ex:
        raise TaskError("Could not check backup: " + ex.__str__())


def perform_backup_cleanup(cfg):
    """
    Performs a cleanup of files and directories which are no longer needed.
    """
    try:
        logging.info("Cleaning up tmp directory.")
        fileutils.clean_tmp()

        total_removed = 0
        for backup in cfg.backups:
            if int(backup.rotationPeriod) != 0:
                archives_to_remove = []
                archive_dates = get_archive_names_and_times(backup.target)
                newest_archive_date = max(archive_dates.items(), key=operator.itemgetter(1))[1]
                oldest_archive_date = newest_archive_date-datetime.timedelta(days=backup.rotationPeriod)

                for archive in archive_dates.keys():
                    if oldest_archive_date > archive_dates[archive]:
                        archives_to_remove.append(archive)
                for archive in archives_to_remove:
                    fileutils.remove_file(archive)

                total_removed += len(archives_to_remove)
                logging.info("Cleaning up old archives at "+backup.target+". Removed a total of "+str(len(archives_to_remove))+" files")

        logging.info("Removed a total of " + str(total_removed) + " old archives.")
    except Exception as ex:
        raise TaskError("Couldn't complete cleanup: " + ex.__str__())


def perform_reporting(msgs, reporter_config):
    """
    Performs email reporting.
    """
    global skipped_backups, inconsistencies_found
    try:
        logging.info("Performing reporting.")

        msg = MIMEText("\n-------------------------------------------------\n".join(msgs))
        subj = "Status " + get_global_status() + " on " + socket.gethostname() + " host. Backups skipped: " + str(skipped_backups) + \
               ". Files missing in archives: " + str(inconsistencies_found) + \
               ". Report as of " + datetime.datetime.now().strftime("%Y-%m-%d-%H:%M")
        msg['Subject'] = reporter_config.subjectPrefix + subj
        msg['From'] = reporter_config.fromAddress
        msg['To'] = reporter_config.toAddress
        s = smtplib.SMTP(reporter_config.smtpConfig.host, int(reporter_config.smtpConfig.port))
        s.starttls()
        s.login(reporter_config.smtpConfig.username, reporter_config.smtpConfig.password)
        s.sendmail(reporter_config.fromAddress, reporter_config.toAddress.split(","), msg.as_string())
        s.quit()

        logging.info("Reporting complete")
    except Exception as ex:
        raise TaskError("Could not perform reporting: " + ex.__str__())


#-----------------------------------------------------------------------------------------------------------------------
# Utility
#-----------------------------------------------------------------------------------------------------------------------
class TaskError(Exception):
     """
     Abstract task utils error.
     """
     def __init__(self, value):
         self.value = value
     def __str__(self):
         return repr(self.value)


class ArchiveIntegrityError(Exception):
     """
     Abstract task utils error.
     """
     def __init__(self, value, inconsistencies=None):
         self.value = value
         self.inconsistencies = inconsistencies
     def __str__(self):
         return repr(self.value) + "\n" + "\n".join(self.inconsistencies if self.inconsistencies else [])


def get_newest_archive_path(dir_path):
    """
    Parses source contents and tries to find file which is assumed to be the latest archive.
    Returns a tuple of the form (absoluteFilePath, modificationTimestamp) or None
    """
    archive_dates = get_archive_names_and_times(dir_path)
    if archive_dates:
        return (max(archive_dates.items(), key=operator.itemgetter(1)))[0]


def get_archive_names_and_times(dir_path):
    """
    Traverses the sourceDir and creates a dict with archive file names as keys and their creation date as value.
    """
    archive_dates = dict()
    archives = fileutils.get_files(dir_path, "^.*-\d+\.tar\.gz$")
    if archives:
        for archive in archives:
            archive_dates[archive] = parse_archive_date(archive)
        return archive_dates


def parse_archive_date(file_name):
    """
    Finds date in the filename and returns a datetime object.
    """
    m = re.search("(?<=-)(\d+)(?=\.tar\.gz)", file_name)
    return datetime.datetime.strptime(m.group(0), "%Y%m%d%H%M")


#-----------------------------------------------------------------------------------------------------------------------
# Misc
#-----------------------------------------------------------------------------------------------------------------------
def process_cli():
    #Handle script arguments
    parser = OptionParser("usage: %prog [options] arg")
    parser.add_option("-v","--verbose",action="store_true",dest="verbose",default=False,help="print log messages to console")
    (options, args) = parser.parse_args()

    log_format = "%(asctime)s [%(levelname)s]:%(module)s - %(message)s"
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG,format=log_format)
    else:
         #Setting up application logger
        logFile = os.path.join(fileutils.get_log_dir(), "rex-backup-"+datetime.datetime.now().strftime("%Y%m%d%H%M")+".log")
        #Will create a new file each time application is executed
        logging.basicConfig(filename=logFile, filemode="w",level=logging.INFO,format=log_format)

if __name__ == '__main__':
    process_cli()
    main()