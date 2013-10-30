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
import operator
from xml.dom.minidom import parse
from shutil import make_archive

from config import BackupConfig

ARCHIVE_TYPE = "gztar"
ARCHIVE_EXT = "tar.gz"
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
    for file in os.listdir(getTmpDir()):
        os.remove(os.path.join(getTmpDir(), file))

def readConfig(fileName):
    """
    Tries to parse a config file located in file working_directory/resources/fileName and returns Configuration object
    read from file or None.
    """
    configFile = os.path.join(getWorkingDir(), "resources", fileName)
    if os.path.exists(configFile):
        dom = parse(configFile)

        #Filling in config values from xml ET
        config = BackupConfig()
        try:
            backup = dom.getElementsByTagName("backup")[0]
            if backup.hasAttribute("backup-downtime"): config.backupDowntime = int(backup.getAttribute("backup-downtime"))
            if backup.hasAttribute("rotation-period"): config.rotationPeriod = int(backup.getAttribute("rotation-period"))
            config.source = backup.getElementsByTagName("source")[0].childNodes[0].data
            config.target = backup.getElementsByTagName("target")[0].childNodes[0].data
        except Exception:
            logging.error("An error occured while trying to parse configuration file. Please check it's formatting and contents.")

        return config
    else:
        logging.error("Could not locate specified configuration file.")

def archive(sourceDir):
    """
    Performs an archiving operation on the source dir and stores the archive in the working_dir/tmp. Returns an absolute
    path to the archived file.
    """
    if isValidDir(sourceDir):
        sourceName = os.path.basename(sourceDir) #Extracts base name
        archiveName = sourceName + "-" + datetime.datetime.now().strftime("%Y%m%d%H%M")
        return make_archive(os.path.join(getTmpDir(),archiveName), ARCHIVE_TYPE, sourceDir)

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

def getLatestArchiveNameAndTime(sourceDir):
    """
    Parses source contents and tries to find file which is assumed to be the latest archive.
    Returns a tuple of the form (absoluteFilePath, modificationTimestamp) or None
    """
    if isValidDir(sourceDir):
        fileMTime = dict()
        for dirpath, dirnames, filenames in os.walk(sourceDir):
            for filename in filenames:
                if filename.endswith(ARCHIVE_EXT):
                    fileMTime[filename] = os.path.getmtime(os.path.join(dirpath, filename))
        fileMTimeTuple = max(fileMTime.items(), key=operator.itemgetter(1))

        return (os.path.join(sourceDir, fileMTimeTuple[0]), fileMTimeTuple[1])

def compareArchiveContents(archiveFilePath, sourceDirPath):
    """
    Traverses contents of the source directory and tries to find matches in tar directory.
    Returns a list of errors or None
    """
    archiveFile = tarfile.open(archiveFilePath, ARCHIVE_MODE)
    tarMembers = dict()
    for member in archiveFile.getmembers():
        tarMembers[member.name] = member.mtime

    srcMembers = dict()
    for dirPath, dirs, files in os.walk(sourceDirPath):
        for f in files:
            srcMembers[os.path.join(dirPath, f)] = os.path.getmtime(os.path.join(dirPath,f))
        for d in dirs:
            srcMembers[os.path.join(dirPath, d)] = os.path.getmtime(os.path.join(dirPath,d))

    errors = []
    for srcKey in srcMembers:
        tarKey = srcKey.replace(sourceDirPath, ".")
        if not (tarKey in tarMembers):
            errors.append(tarKey + " is missing in the tar")
        elif datetime.date.fromtimestamp(srcMembers[srcKey]) != datetime.date.fromtimestamp(tarMembers[tarKey]):
            errors.append(tarKey + " has wrong mtime: tar=" + str(tarMembers[tarKey]) + " src=" + str(srcMembers[member]))

    if len(errors) > 0:
        return errors

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