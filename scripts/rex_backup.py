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
import re

__author__ = "Denys Sobchyshak"
__email__ = "denys.sobchyshak@gmail.com"
__version__ = 1.0

import logging
import datetime
import time
import smtplib
import operator
import socket, os
from email.mime.text import MIMEText
from optparse import OptionParser

import fileutils
import config

ARCHIVE_FORMATS = ["zip", "tar", "bztar", "gztar"]

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

messages = []
status = Status.Success
skippedBackups = 0
inconsistenciesFound = 0

#-----------------------------------------------------------------------------------------------------------------------
# General functions
#-----------------------------------------------------------------------------------------------------------------------
def getGlobalStatus():
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

def addMessage(status, taskType, location, message=""):
    """
    Adds provided info to the messages.
    """
    global messages
    template = getTemplateByStatus(status)
    messages.append(status + ": " + (template % {"what": taskType, "where": location}) + "\n" + message)

def getTemplateByStatus(status):
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
    global status, skippedBackups, inconsistenciesFound
    #Processing configuration
    rexConfig = None
    try:
        configFilePath = os.path.join(fileutils.getWorkingDir(), "resources", "config.xml")
        logging.info("Reading config file: " + configFilePath)
        rexConfig = config.readConfig(configFilePath)
    except Exception as ex:
        logging.fatal("Failed to parse configuration file. Reason: " + ex.__str__())

    if rexConfig:
        #step 1:performing backups
        if len(rexConfig.backups) > 0:
            for backup in rexConfig.backups:
                if not isDowntimePeriod(backup): #don't do backups if it's a downtime period
                    try: #try to perform backup
                        performBackup(backup)
                        addMessage(Status.Success, Tasks.Backup, backup.source)
                    except Exception as ex:
                        addMessage(Status.Failed, Tasks.Backup,backup.source,ex.__str__())
                        logging.error("Failed to perform backup: " + ex.__str__())
                        break #no need to continue the loop if backup failed
                    try:#try to perform backup check
                        if rexConfig.performChecks:
                            performBackupCheck(backup)
                            addMessage(Status.Success, Tasks.Check, backup.source)
                    except ArchiveIntegrityError as ex:
                        addMessage(Status.Failed, Tasks.Check,backup.source,ex.__str__())
                        logging.error("Backup check found some archive inconsistencies: " + ex.__str__())
                        inconsistenciesFound+=len(ex.inconsistencies)
                    except Exception as ex:
                        addMessage(Status.Failed, Tasks.Check,backup.source,ex.__str__())
                        logging.error("Failed to perform backup check: " + ex.__str__())
                else:
                    skippedBackups+=1
                    addMessage(Status.Skipped, Tasks.Backup, backup.source)
                fileutils.cleanTmp()
            if skippedBackups == len(rexConfig.backups):
                status = Status.Skipped

        #step 2:performing cleanup
        try:
            performBackupCleanup(rexConfig)
            addMessage(Status.Success, Tasks.Cleanup, fileutils.getTmpDir())
        except Exception as ex:
            addMessage(Status.Failed, Tasks.Cleanup, fileutils.getTmpDir(), ex.__str__())
            logging.error("Failed to perform backup cleanup: " + ex.__str__())

        #step 3: performing reporting
        try:
            if rexConfig.performReporting:
                performReporting(messages, rexConfig.reporterConfig)
        except Exception as ex:
            logging.error("Failed to perform reporting: " + ex.__str__())

def isDowntimePeriod(backupConfig):
    if int(backupConfig.backupDowntime) == 0:
        return False
    else:
        archivePath = getNewestArchivePath(backupConfig.target)
        if archivePath: #if there was no archive we don't need to check anything
            lastBackupTime = parseArchiveDate(archivePath).date()
            nextBackUpTime = lastBackupTime + datetime.timedelta(days=int(backupConfig.backupDowntime))
            now = datetime.date.fromtimestamp(time.time())
            if now < nextBackUpTime:
                return True
        else:
            return False

def performBackup(backupConfig):
    """
    Performs backup according to provided config.
    """
    try:
        logging.info("Performing backup task: " + backupConfig.__str__())

        logging.info("Archiving directory: " + backupConfig.source)
        archiveFilePath = fileutils.archiveDir(backupConfig.source, ARCHIVE_FORMATS[3])
        logging.info("Copying archive to target directory: " + backupConfig.target)
        fileutils.copyFile(archiveFilePath, backupConfig.target)

        logging.info("Backup complete")
    except Exception as ex:
        raise TaskError("Failed to perform backup: " + ex.__str__())

def performBackupCheck(backupConfig):
    """
    Checks if backup was performed correctly according to specified config.
    """
    try:
        logging.info("Checking backup: " + backupConfig.__str__())

        archive_path = getNewestArchivePath(backupConfig.target)
        if not archive_path:
            raise TaskError("No archive was found in the target dir: " + backupConfig.target)
        logging.info("Copying newest archive: " + archive_path)
        tmp_archive = fileutils.copyFile(archive_path, fileutils.getTmpRemoteDir())
        logging.info("Checking archive consistency.")
        inconsistencies = fileutils.compareArchiveAgainstDir(tmp_archive, backupConfig.source, backupConfig.excludeRegexp)

        logging.info("Backup check completed")
        if inconsistencies:
            raise ArchiveIntegrityError("Found inconsistencies while checking archive and source.", inconsistencies)
    except ArchiveIntegrityError as ex:
        raise ex
    except Exception as ex:
        raise TaskError("Could not check backup: " + ex.__str__())

def performBackupCleanup(config):
    """
    Performs a cleanup of files and directories which are no longer needed.
    """
    try:
        logging.info("Cleaning up tmp directory.")
        fileutils.cleanTmp()

        totalRemoved = 0
        for backup in config.backups:
            if int(backup.rotationPeriod) != 0:
                archivesToRemove = []
                archiveDates = getArchiveNamesAndTimes(backup.target)
                newestArchiveDate = max(archiveDates.items(), key=operator.itemgetter(1))[1]
                oldestArchiveDate = newestArchiveDate-datetime.timedelta(days=backup.rotationPeriod)

                for archive in archiveDates.keys():
                    if oldestArchiveDate > archiveDates[archive]:
                        archivesToRemove.append(archive)
                for archive in archivesToRemove:
                    fileutils.removeFile(archive)

                totalRemoved+=len(archivesToRemove)
                logging.info("Cleaning up old archives at "+backup.target+". Removed a total of "+str(len(archivesToRemove))+" files")

        logging.info("Removed a total of " + str(totalRemoved) + " old archives.")
    except Exception as ex:
        raise TaskError("Couldn't complete cleanup: " + ex.__str__())

def performReporting(messages, reporterConfig):
    """
    Performs email reporting.
    """
    global skippedBackups, inconsistenciesFound
    try:
        logging.info("Performing reporting.")

        msg = MIMEText("\n-------------------------------------------------\n".join(messages))
        subj = "Status " + getGlobalStatus() + " on " + socket.gethostname() + " host. Backups skipped: " + str(skippedBackups) + \
               ". Files missing in archives: " + str(inconsistenciesFound) + \
               ". Report as of " + datetime.datetime.now().strftime("%Y-%m-%d-%H:%M")
        msg['Subject'] = reporterConfig.subjectPrefix + subj
        msg['From'] = reporterConfig.fromAddress
        msg['To'] = reporterConfig.toAddress
        s = smtplib.SMTP(reporterConfig.smtpConfig.host, int(reporterConfig.smtpConfig.port))
        s.starttls()
        s.login(reporterConfig.smtpConfig.username, reporterConfig.smtpConfig.password)
        s.sendmail(reporterConfig.fromAddress, reporterConfig.toAddress.split(","), msg.as_string())
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

def getNewestArchivePath(dirPath):
    """
    Parses source contents and tries to find file which is assumed to be the latest archive.
    Returns a tuple of the form (absoluteFilePath, modificationTimestamp) or None
    """
    archiveDates = getArchiveNamesAndTimes(dirPath)
    if archiveDates:
        return (max(archiveDates.items(), key=operator.itemgetter(1)))[0]

def getArchiveNamesAndTimes(dirPath):
    """
    Traverses the sourceDir and creates a dict with archive file names as keys and their creation date as value.
    """
    archiveDates = dict()
    archives = fileutils.getFiles(dirPath, "^.*-\d+\.tar\.gz$")
    if archives:
        for archive in archives:
            archiveDates[archive] = parseArchiveDate(archive)
        return archiveDates

def parseArchiveDate(fileName):
    """
    Finds date in the filename and returns a datetime object.
    """
    m = re.search("(?<=-)(\d+)(?=\.tar\.gz)", fileName)
    return datetime.datetime.strptime(m.group(0), "%Y%m%d%H%M")

#-----------------------------------------------------------------------------------------------------------------------
# Misc
#-----------------------------------------------------------------------------------------------------------------------
def processCLI():
    #Handle script arguments
    parser = OptionParser("usage: %prog [options] arg")
    parser.add_option("-v","--verbose",action="store_true",dest="verbose",default=False,help="print log messages to console")
    (options, args) = parser.parse_args()

    logFormat = "%(asctime)s [%(levelname)s]:%(module)s - %(message)s"
    if options.verbose:
        logging.basicConfig(level=logging.DEBUG,format=logFormat)
    else:
         #Setting up application logger
        logFile = os.path.join(fileutils.getLogDir(), "rex-backup-"+datetime.datetime.now().strftime("%Y%m%d%H%M")+".log")
        #Will create a new file each time application is executed
        logging.basicConfig(filename=logFile, filemode="w",level=logging.INFO,format=logFormat)

if __name__ == '__main__':
    processCLI()
    main()