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

import logging
import datetime
import time
import smtplib
import operator
import socket
from email.mime.text import MIMEText

import fileutils

class Status:
    SUCCESS = "OK"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"

class Messages:
    FAILED = "Failed to perform %(what)s on %(where)s."
    SUCCESS = "Successfully performed %(what)s on %(where)s."
    SKIPPED = "Skipped %(what)s on %(where)s."

class Tasks:
    BACKUP = "BackupTask"
    CHECK = "BackupCheckTask"
    CLEANUP = "CleanupTask"

messages = []
status = Status.SUCCESS

def main():
    logging.info("Reading config file...")
    config = fileutils.readConfig("config.xml")

    #Processing backups
    if len(config.backups) > 0:
        skipCount = 0
        for backup in config.backups:
            backupStatus = (Status.SKIPPED, "")
            checkStatus = (Status.SKIPPED, "")

            #Don't do backups if we are in the downtime period
            isDowntimePeriod = False
            if int(backup.backupDowntime) != 0:
                archiveTimeTuple = getNewestArchiveNameAndTime(backup.target)
                if archiveTimeTuple: #if there was no archive we don't need to check anything
                    lastBackupTime = archiveTimeTuple[1].date()
                    now = datetime.date.fromtimestamp(time.time())
                    nextBackUpTime = lastBackupTime + datetime.timedelta(days=int(backup.backupDowntime))
                    if now < nextBackUpTime:
                        isDowntimePeriod = True
            if not isDowntimePeriod:
                backupStatus = performBackupTask(backup)
                if config.performChecks:
                    checkStatus = performBackupCheck(backup)
            else:
                skipCount+=1
            #Adding messages for reporting
            addMessage(backupStatus, Tasks.BACKUP, backup.source)
            addMessage(checkStatus, Tasks.CHECK, backup.source)

        if skipCount == len(config.backups): status = Status.SKIPPED

    cleanupStatus = performBackupCleanup(config)
    addMessage(cleanupStatus, Tasks.CLEANUP, fileutils.getTmpDir())

    if config.performReporting:
        performReporting(messages, config.reporterConfig)

def addMessage(statusTuple, taskType, location):
    """
    Adds provided info to the messages.
    """
    template = getTemplateByStatus(statusTuple[0])
    messages.append(statusTuple[0] + ": " + (template % {"what": taskType, "where": location}) + "\n" + statusTuple[1])

def getGlobalStatus():
    """
    Parses global status and messages and determines real status of a backup.
    """
    if status == Status.SKIPPED:
        return status
    for m in messages:
        if m.startswith(Status.FAILED):
            return Status.FAILED
    return Status.SUCCESS

def getTemplateByStatus(status):
    """
    Parses status and return corresponding template
    """
    if status == Status.SUCCESS:
        return Messages.SUCCESS
    elif status == Status.FAILED:
        return Messages.FAILED
    elif status == Status.SKIPPED:
        return Messages.SKIPPED

def performBackupTask(backupConfig):
    """
    Performs backup according to provided config.
    """
    try:
        logging.info("Backing up " + backupConfig.__str__())
        logging.info("Archiving source directory")
        archiveFile = fileutils.archiveDir(backupConfig.source)
        logging.info("Copying archive to the target")
        fileutils.copyFile(archiveFile, backupConfig.target)
        logging.info("Backup complete")
        return (Status.SUCCESS, "")
    except Exception as ex:
        logging.error("Next error occurred: \n" + ex.__str__())
        return (Status.FAILED, "Next errors occurred: \n" + ex.__str__())

def performBackupCheck(backupConfig):
    """
    Checks if backup was performed correctly according to specified config.
    """
    try:
        logging.info("Checking backup of " + backupConfig.__str__())
        logging.info("Copying latest archive to tmp dir.")
        latestArchiveName = getNewestArchiveNameAndTime(backupConfig.target)[0]
        if not latestArchiveName:
            m = "Couldn't find archive to be checked."
            logging.error(m)
            return (Status.FAILED, m)

        tmpArchive = fileutils.copyFile(latestArchiveName, fileutils.getTmpRemoteDir())
        logging.info("Comparing tree listings and file modification dates.")
        errors = fileutils.compareArchiveContents(tmpArchive, backupConfig.source)
        logging.info("Backup check completed")

        if errors:
            logging.error("Next errors were occurred while comparing archive and source: \n" + "\n".join(errors))
            return (Status.FAILED, errors)
        if not errors:
            return (Status.SUCCESS, "")
    except Exception as ex:
        logging.error("Next errors occurred: \n" + ex.__str__())
        return (Status.FAILED, "Next errors occurred: \n" + ex.__str__())

def performReporting(messages, reporterConfig):
    """
    Performs email reporting.
    """
    msg = MIMEText("\n".join(messages))
    subj = "Status " + status + " on " + socket.gethostname() + " host. Report as of " + datetime.datetime.now().strftime("%Y-%m-%d-%H:%M")
    msg['Subject'] = reporterConfig.subjectPrefix + subj
    msg['From'] = reporterConfig.fromAddress
    msg['To'] = reporterConfig.toAddress
    s = smtplib.SMTP(reporterConfig.smtpConfig.host, int(reporterConfig.smtpConfig.port))
    s.starttls()
    s.login(reporterConfig.smtpConfig.username, reporterConfig.smtpConfig.password)
    s.sendmail(reporterConfig.fromAddress, reporterConfig.toAddress.split(","), msg.as_string())
    s.quit()
    logging.info("Reporting complete")

def performBackupCleanup(config):
    """
    Performs a cleanup of files and directories which are no longer needed.
    """
    try:
        logging.info("Cleaning up tmp directory.")
        fileutils.cleanTmp()

        if int(config.rotationPeriod) != 0:
            totalRemoved = 0
            for backup in config.backups:
                archivesToRemove = []
                archiveDates = getArchiveNamesAndTimes(backup.target)
                newestArchiveDate = max(archiveDates.items(), key=operator.itemgetter(1))[1]
                oldestArchiveDate = newestArchiveDate-datetime.timedelta(days=config.rotationPeriod)

                for archive in archiveDates.keys():
                    if oldestArchiveDate > archiveDates[archive]:
                        archivesToRemove.append(archive)

                for archive in archivesToRemove:
                    fileutils.removeFile(archive)
                totalRemoved+=len(archivesToRemove)
                logging.info("Cleaning up old archives at "+backup.target+". Removed a total of "+str(len(archivesToRemove))+" files")
            return (Status.SUCCESS, "Removed a total of " + str(totalRemoved) + " old archives.")
    except Exception as ex:
        logging.error("Next exception occurred: \n" + ex.__str__())
        return (Status.FAILED, "Next exception occured: " + ex.__str__())

def getNewestArchiveNameAndTime(dirPath):
    """
    Parses source contents and tries to find file which is assumed to be the latest archive.
    Returns a tuple of the form (absoluteFilePath, modificationTimestamp) or None
    """
    archiveDates = getArchiveNamesAndTimes(dirPath)
    if archiveDates:
        return max(archiveDates.items(), key=operator.itemgetter(1))

def getArchiveNamesAndTimes(dirPath):
    """
    Traverses the sourceDir and creates a dict with archive file names as keys and their creation date as value.
    """
    archiveDates = dict()
    archives = fileutils.getArchiveFiles(dirPath)
    if archives:
        for archive in archives:
            archiveDates[archive] = fileutils.parseArchiveDate(archive)
        return archiveDates


if __name__ == '__main__':
    #Setting up application logger
    #logFile = os.path.join(fileutils.getLogDir(), "rex-backup-"+datetime.datetime.now().strftime("%Y%m%d%H%M")+".log")
    logFormat = "%(asctime)s [%(levelname)s]:%(module)s - %(message)s"
    #Will create a new file each time application is executed
    #logging.basicConfig(filename=logFile, filemode="w",level=logging.INFO,format=logFormat)
    logging.basicConfig(level=logging.DEBUG,format=logFormat)
    main()