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

    #Don't do backups if we are in the downtime period
    isDowntimePeriod = False
    if int(config.backupDowntime) != 0:
        archiveTimeTuple = getNewestArchiveNameAndTime(config.target)
        if archiveTimeTuple: #if there was no archive we don't need to check anything
            lastBackupTime = archiveTimeTuple[1].date()
            now = datetime.date.fromtimestamp(time.time())
            nextBackUpTime = lastBackupTime + datetime.timedelta(days=int(config.backupDowntime))
            if now < nextBackUpTime:
                isDowntimePeriod = True

    if not isDowntimePeriod:
        performBackupTask(config)

    if config.performChecks:
        performBackupCheck(config)

    if config.performTmpCleanup:
        performBackupCleanup()

    if int(config.rotationPeriod) != 0:
        performArchiveFilesRotation(config)

def performBackupTask(config):
    """
    Performs backup according to provided config.
    """
    logging.info("BACKUP STARTED")
    logging.info("Archiving source directory.")
    archiveFile = fileutils.archiveDir(config.source)
    #logging.info("Generating MD5 file.")
    #archiveMD5File = fileutils.generateMD5File(archiveFile)
    logging.info("Copying archive to the target.")
    targetArchiveFile = fileutils.copyFile(archiveFile, config.target)
    #logging.info("Copying MD5 file to the target.")
    #targetArchiveMD5File = fileutils.copyFile(archiveMD5File, config.target)
    logging.info("BACKUP COMPLETE")

def performBackupCheck(config):
    """
    Checks if backup was performed correctly according to specified config.
    """
    logging.info("CHECKING BACKUP")
    logging.info("Copying latest archive to tmp dir.")
    latestArchiveName = getNewestArchiveNameAndTime(config.target)[0]
    if not latestArchiveName:
        logging.error("Check FAILED. No archive file found.")
    tmpArchive = fileutils.copyFile(latestArchiveName, fileutils.getTmpDir())

    logging.info("Comparing tree listings and file modification dates.")
    errors = fileutils.compareArchiveContents(tmpArchive, config.source)
    if errors:
        logging.error("Inconsistencies found between archive and source.")
        logging.error("Next errors were encountered: " + errors)

    if config.checkerConfig.sendReports:
        logging.info("Sending reports.")
        sendReport(errors, config.checkerConfig.reporterConfig)
    logging.info("BACKUP CHECK COMPLETE")

def sendReport(errors, reporterConfig):
    msg = MIMEText("Next errors were encountered: " + errors) if errors else MIMEText("Backup was completed successfully")
    msg['Subject'] = reporterConfig.subjectPrefix + "Status report as of " + datetime.datetime.now().strftime("%Y-%m-%d-%H:%M")
    msg['From'] = reporterConfig.fromAddress
    msg['To'] = reporterConfig.toAddress

    s = smtplib.SMTP(reporterConfig.smtpConfig.host, int(reporterConfig.smtpConfig.port))
    s.starttls()
    s.login(reporterConfig.smtpConfig.username, reporterConfig.smtpConfig.password)
    s.sendmail(reporterConfig.fromAddress, reporterConfig.toAddress.split(","), msg.as_string())
    s.quit()

def performBackupCleanup():
    """
    Performs a cleanup of files and directories which are no longer needed.
    """
    logging.info("Cleaning up tmp directory.")
    fileutils.cleanTmp()

def performArchiveFilesRotation(config):
    """
    Removes archives which are too old to be stored.
    """
    logging.info("Cleaning up old archives.")
    archivesToRemove = []

    archiveDates = getArchiveNamesAndTimes(config.target)
    newestArchiveDate = max(archiveDates.items(), key=operator.itemgetter(1))[1]
    oldestArchiveDate = newestArchiveDate-datetime.timedelta(days=config.rotationPeriod)

    for archive in archiveDates.keys():
        if oldestArchiveDate > archiveDates[archive]:
            archivesToRemove.append(archive)

    for archive in archivesToRemove:
        fileutils.removeFile(archive)
    logging.info(str(len(archivesToRemove)) + " old archives were removed.")

def getNewestArchiveNameAndTime(sourceDir):
    """
    Parses source contents and tries to find file which is assumed to be the latest archive.
    Returns a tuple of the form (absoluteFilePath, modificationTimestamp) or None
    """
    archiveDates = getNewestArchiveNameAndTime(sourceDir)
    return max(archiveDates.items(), key=operator.itemgetter(1))

def getArchiveNamesAndTimes(sourceDir):
    """
    Traverses the sourceDir and creates a dict with archive file names as keys and their creation date as value.
    """
    archives = fileutils.getArchiveFiles(sourceDir)
    archiveDates = dict()
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