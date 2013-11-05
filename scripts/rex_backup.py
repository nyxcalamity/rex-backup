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
from email.mime.text import MIMEText

import fileutils

def main():
    logging.info("Reading config file...")
    config = fileutils.readConfig("config.xml")

    messages = []
    #Processing backups
    for backup in config.backups:
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
            performBackupTask(backup)
        if config.performChecks:
            addMessages(messages,performBackupCheck(backup))

    performBackupCleanup(config)

    if config.performReporting:
        performReporting(messages, config.reporterConfig)

def addMessages(targetList, messages):
    if messages:
        for msg in messages:
            targetList.append(msg)

def performBackupTask(backupConfig):
    """
    Performs backup according to provided config.
    """
    logging.info("Started backup for: " + backupConfig.__str__())
    logging.info("Archiving source directory")
    archiveFile = fileutils.archiveDir(backupConfig.source)
    logging.info("Copying archive to the target")
    fileutils.copyFile(archiveFile, backupConfig.target)
    logging.info("Backup complete")

def performBackupCheck(backupConfig):
    """
    Checks if backup was performed correctly according to specified config.
    """
    logging.info("Started backup check for: " + backupConfig.__str__())
    logging.info("Copying latest archive to tmp dir.")
    latestArchiveName = getNewestArchiveNameAndTime(backupConfig.target)[0]
    if not latestArchiveName:
        logging.error("Check FAILED. No archive file found.")
    tmpArchive = fileutils.copyFile(latestArchiveName, fileutils.getTmpDir())
    logging.info("Comparing tree listings and file modification dates.")
    errors = fileutils.compareArchiveContents(tmpArchive, backupConfig.source)
    if errors:
        logging.error("Inconsistencies found between archive and source.")
        logging.error("Next errors were encountered: ".join(errors))
    logging.info("Backup check completed")

def performReporting(errors, reporterConfig):
    """
    Performs email reporting.
    """
    msg = MIMEText("Next errors were encountered: " + errors) if errors else MIMEText("Backup was completed successfully")
    msg['Subject'] = reporterConfig.subjectPrefix + "Status report as of " + datetime.datetime.now().strftime("%Y-%m-%d-%H:%M")
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
    logging.info("Cleaning up tmp directory.")
    fileutils.cleanTmp()

    if int(config.rotationPeriod) != 0:
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
            logging.info("Cleaning up old archives at "+backup.target+". Removed a total of "+str(len(archivesToRemove))+" files")

def getNewestArchiveNameAndTime(dirPath):
    """
    Parses source contents and tries to find file which is assumed to be the latest archive.
    Returns a tuple of the form (absoluteFilePath, modificationTimestamp) or None
    """
    archiveDates = getArchiveNamesAndTimes(dirPath)
    return max(archiveDates.items(), key=operator.itemgetter(1))

def getArchiveNamesAndTimes(dirPath):
    """
    Traverses the sourceDir and creates a dict with archive file names as keys and their creation date as value.
    """
    archiveDates = dict()
    for archive in fileutils.getArchiveFiles(dirPath):
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