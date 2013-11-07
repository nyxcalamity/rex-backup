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

import os
import sys
import shutil
import tarfile
import time
import datetime
import logging
import hashlib
import re
from xml.dom.minidom import parse
from shutil import make_archive

from config import *

ARCHIVE_TYPE = "gztar"
ARCHIVE_EXT = "tar.gz"
ARCHIVE_EXT_PATTERN = "\.tar\.gz"
ARCHIVE_NAME_PATTERN = "^.*-\d+"+ARCHIVE_EXT_PATTERN+"$"
ARCHIVE_MODE = "r:gz"

def getWorkingDir():
    """
    Returns script working directory. (Parent directory of the script that invoked python interpreter)
    """
    return os.path.join(sys.path[0], os.pardir)

def getTmpDir():
    """
    Returns path to the temporary directory. Creates one if it didn't exist.
    """
    tmpDir =  os.path.join(getWorkingDir(), "tmp")
    if not os.path.exists(tmpDir):
        os.makedirs(tmpDir)
    return tmpDir

def getTmpLocalDir():
    """
    Returns path to the temporary directory. Creates one if it didn't exist.
    """
    tmpDir =  os.path.join(getTmpDir(), "local")
    if not os.path.exists(tmpDir):
        os.makedirs(tmpDir)
    return tmpDir

def getTmpRemoteDir():
    """
    Returns path to the temporary directory. Creates one if it didn't exist.
    """
    tmpDir =  os.path.join(getTmpDir(), "remote")
    if not os.path.exists(tmpDir):
        os.makedirs(tmpDir)
    return tmpDir

def getLogDir():
    """
    Returns path to the log directory. Creates one if it didn't exist.
    """
    logDir = os.path.join(getWorkingDir(), "logs")
    if not os.path.exists(logDir):
        os.makedirs(logDir)
    return logDir

def cleanTmp():
    """
    Deletes all files in the temp directory.
    """
    shutil.rmtree(getTmpDir())

def readConfig(fileName):
    """
    Tries to parse a config file located in file working_directory/resources/fileName and returns Configuration object
    read from file or None.
    """
    configFile = os.path.join(getWorkingDir(), "resources", fileName)
    if os.path.exists(configFile):
        dom = parse(configFile)

        #Filling in config values from xml ET
        rexConfig = RexConfig()
        try:
            #Parsing general configuration
            config = dom.getElementsByTagName("config")[0]
            if config.hasAttribute("rotation-period"): rexConfig.rotationPeriod = int(config.getAttribute("rotation-period"))
            if config.hasAttribute("perform-checks"): rexConfig.performChecks = bool(config.getAttribute("perform-checks"))
            if config.hasAttribute("perform-reporting"): rexConfig.performReporting = bool(config.getAttribute("perform-reporting"))

            #Parsing configuration of backups
            rexConfig.backups = []
            backups = config.getElementsByTagName("backups")[0]
            for backup in backups.getElementsByTagName("backup"):
                backupCfg = BackupConfig()
                if backup.hasAttribute("backup-downtime"): backupCfg.backupDowntime = int(backup.getAttribute("backup-downtime"))
                backupCfg.source = backup.getElementsByTagName("source")[0].childNodes[0].data
                backupCfg.target = backup.getElementsByTagName("target")[0].childNodes[0].data
                rexConfig.backups.append(backupCfg)

            #Parsing configuration of reporter
            reporterConfig = ReporterConfig()
            reporter = config.getElementsByTagName("reporter")[0]
            if reporter.hasAttribute("from-address"): reporterConfig.fromAddress = reporter.getAttribute("from-address")
            if reporter.hasAttribute("to-address"): reporterConfig.toAddress = reporter.getAttribute("to-address")
            if reporter.hasAttribute("subject-prefix"): reporterConfig.subjectPrefix = reporter.getAttribute("subject-prefix")
            rexConfig.reporterConfig = reporterConfig

            #Parsing smtp configuration
            smtpConfig = SmtpConfig()
            smtp = reporter.getElementsByTagName("smtp")[0]
            if smtp.hasAttribute("host"): smtpConfig.host = smtp.getAttribute("host")
            if smtp.hasAttribute("port"): smtpConfig.port = smtp.getAttribute("port")
            if smtp.hasAttribute("username"): smtpConfig.username = smtp.getAttribute("username")
            if smtp.hasAttribute("password"): smtpConfig.password = smtp.getAttribute("password")
            reporterConfig.smtpConfig = smtpConfig

        except Exception:
            logging.error("An error occurred while trying to parse configuration file. Please check it's formatting and contents.")

        return rexConfig
    else:
        logging.error("Could not locate specified configuration file.")

def archiveDir(sourceDir):
    """
    Performs an archiving operation on the source dir and stores the archive in the working_dir/tmp. Returns an absolute
    path to the archived file.
    """
    if isValidDir(sourceDir):
        sourceName = os.path.basename(sourceDir) #Extracts base name
        archiveName = sourceName + "-" + datetime.datetime.now().strftime("%Y%m%d%H%M")
        return make_archive(os.path.join(getTmpLocalDir(),archiveName), ARCHIVE_TYPE, sourceDir)

def generateMD5File(sourceFile):
    """
    Generates an md5 code for a source file and returns the absolute path to the file.
    """
    if isValidFile(sourceFile):
        md5Str = sourceFile + "-" + str(time.time())
        #Apparently md5 algo operates on bytes, that's why we need to encode the string
        m = hashlib.md5(md5Str.encode("utf-8"))
        md5File = open(sourceFile+".md5","w")
        md5File.write(m.hexdigest() + "\t" + os.path.basename(sourceFile))
        md5File.close()
        return md5File.name

def copyFile(sourceFile, targetDir):
    """
    Copies source file to the target dir. Returns absolute path to the target file or none.
    """
    if isValidFile(sourceFile):
        if not isValidDir(targetDir):
            logging.info("Trying to create " + targetDir)
            try:
                os.makedirs(targetDir)
                logging.info("Created: " + targetDir)
            except Exception:
                logging.error("Couldn't create: " + targetDir + ". Target location can't be reached.")

        targetFile = os.path.join(targetDir , os.path.basename(sourceFile))
        shutil.copyfile(sourceFile, targetFile)
        return targetFile

def removeFile(filePath):
    """
    Removes a file from the FS. Returns true if succeeded and None otherwise.
    """
    if isValidFile(filePath):
        os.remove(filePath)
        return True

def getArchiveFiles(sourceDir):
    """
    Searches sourceDir for archive files.
    """
    if isValidDir(sourceDir):
        archives = []
        for dirpath, dirnames, filenames in os.walk(sourceDir):
            for filename in filenames:
                if re.search(ARCHIVE_NAME_PATTERN, filename):
                    archives.append(os.path.join(dirpath, filename))
        return archives

def parseArchiveDate(fileName):
    """
    Finds date in the filename and returns a datetime object.
    """
    m = re.search("(?<=-)(\d+)(?="+ARCHIVE_EXT_PATTERN+")", fileName)
    return datetime.datetime.strptime(m.group(0), "%Y%m%d%H%M")

def compareArchiveContents(archiveFilePath, sourceDirPath):
    """
    Traverses contents of the source directory and tries to find matches in the archive. Will ignore links. Returns a
    list of errors or None.
    """
    archiveFile = tarfile.open(archiveFilePath, ARCHIVE_MODE)
    tarMembers = dict()
    for member in archiveFile.getmembers():
        tarMembers[member.name] = member.mtime

    #TODO: think of a more elegant way of ignoring symlinks (not adding them to archive at all?)
    srcMembers = dict()
    for dirPath, dirs, files in os.walk(sourceDirPath):
        for f in files:
            if not os.path.islink(os.path.join(dirPath, f)):
                srcMembers[os.path.join(dirPath, f)] = os.path.getmtime(os.path.join(dirPath,f))
        for d in dirs:
            if not os.path.islink(os.path.join(dirPath, d)):
                srcMembers[os.path.join(dirPath, d)] = os.path.getmtime(os.path.join(dirPath,d))

    errors = []
    for srcKey in srcMembers:
        tarKey = srcKey.replace(sourceDirPath, ".")
        if not (tarKey in tarMembers):
            tarKey += os.path.sep #For some reason some folders have separator concatenated to the path.
            if not (tarKey in tarMembers):
                errors.append(tarKey + " is missing in the archive")
        elif datetime.date.fromtimestamp(srcMembers[srcKey]) != datetime.date.fromtimestamp(tarMembers[tarKey]):
            errors.append(tarKey + " has wrong mtime timestamp: archive=" + timestampToString(tarMembers[tarKey]) + \
                          " src=" + timestampToString(srcMembers[srcKey]))

    if len(errors) > 0:
        return errors

def timestampToString(timestamp):
    """
    Gets a timestamp and creates a formatted date string out of that timestamp.
    """
    return datetime.date.fromtimestamp(timestamp).strftime("%Y-%m-%d-%H:%M")

def isValidFile(path):
    """
    Checks if the provided path corresponds to a file.
    """
    if not os.path.isfile(path):
        logging.error("Provided path is not a valid file path.(" + path + ")")
        return False
    return True

def isValidDir(path):
    """
    Checks if the provided path corresponds to a directory.
    """
    if not os.path.isdir(path):
        logging.error("Provided path is not a valid dir path.(" + path + ")")
        return False
    return True