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
import time
import datetime
import logging
import hashlib
import operator
from xml.dom.minidom import parse
from shutil import make_archive

from config import Config
from config import ConfigError


class FileUtils:
    """
    Provides major file operations like archiving, directory tree listing, config parsing and etc.
    """

    @staticmethod
    def getWorkingDir():
        """
        Returns application working directory. (Parent directory of the script that invoked python interpreter)
        """
        return os.path.join(sys.path[0], os.pardir)

    @staticmethod
    def getTmpDir():
        """
        Returns path to the temporary directory. Creates one if it didn't exist.
        """
        tmpDir =  os.path.join(FileUtils.getWorkingDir(), "tmp")
        if not os.path.exists(tmpDir):
            os.makedirs(tmpDir)
        return tmpDir

    @staticmethod
    def cleanTmp():
        """
        Deletes all archives by ARCHIVE_PREFIX from temporary directory.
        """
        for file in os.listdir(FileUtils.getTmpDir()):
            os.remove(os.path.join(FileUtils.getTmpDir(), file))

    @staticmethod
    def getLogDir():
        """
        Returns path to the log directory. Creates one if it didn't exist.
        """
        logDir = os.path.join(FileUtils.getWorkingDir(), "logs")
        if not os.path.exists(logDir):
            os.makedirs(logDir)
        return logDir

    @staticmethod
    def readConfig(fileName):
        """
        Tries to parse a config file located in file working_directory/resources/fileName.

        Returns:Configuration object read from file.
        Throws: ConfigError
        """
        configFile = os.path.join(FileUtils.getWorkingDir(), "resources", fileName)
        if os.path.exists(configFile):
            dom = parse(configFile)

            #Filling in config values from xml ET
            config = Config()
            try:
                backup = dom.getElementsByTagName("backup")[0]
                if backup.hasAttribute("backup-downtime"): config.backupDowntime = int(backup.getAttribute("backup-downtime"))
                if backup.hasAttribute("rotation-period"): config.rotationPeriod = int(backup.getAttribute("rotation-period"))
                config.source = backup.getElementsByTagName("source")[0].childNodes[0].data
                config.target = backup.getElementsByTagName("target")[0].childNodes[0].data
            except Exception:
                msg = "An error occured while trying to parse configuration file. Please check it's formatting and contents."
                logging.error(msg)
                raise ConfigError(msg)

            return config
        else:
            msg = "Could not locate specified configuration file."
            logging.error(msg)
            raise ConfigError(msg)

    @staticmethod
    def archive(sourceDir):
        """
        Performs an archiving operation on the source (both file and dir) and stores the archive in the working_dir/tmp.

        Returns:
        Absolute path to the archived file.
        """
        if FileUtils.isValidDir(sourceDir):
            sourceName = os.path.basename(sourceDir) #Extracts base name
            archiveName = sourceName + "-" + datetime.datetime.now().strftime("%Y%m%d%H%M")
            return make_archive(os.path.join(FileUtils.getTmpDir(),archiveName), 'gztar', sourceDir)

    @staticmethod
    def generateMD5File(sourceFile):
        if FileUtils.isValidFile(sourceFile):
            md5Str = sourceFile + "-" + str(time.time())
            #Apparently md5 algo operates on bytes, that's why we need to encode the string
            m = hashlib.md5(md5Str.encode("utf-8"))
            md5File = open(sourceFile+".md5","w")
            md5File.write(m.hexdigest() + "\t" + os.path.basename(sourceFile))
            md5File.close()
            return md5File.name

    @staticmethod
    def copy(sourceFile, targetDir):
        """
        Copies source file to the target dir.

        Returns:Absolute path to the target file.
        Throws: FileUtilsError
        """
        if FileUtils.isValidFile(sourceFile):
            if not FileUtils.isValidDir(targetDir):
                logging.info("Trying to create " + targetDir)
                try:
                    os.makedirs(targetDir)
                    logging.info("Created: " + targetDir)
                except Exception:
                    logging.error("Couldn't create: " + targetDir + ". Target location can't be reached.")

            targetFile = os.path.join(targetDir , os.path.basename(sourceFile))
            shutil.copyfile(sourceFile, targetFile)
            return targetFile

    @staticmethod
    def getLatestArchive(sourceDir):
        """
        Parses source contents and tries to find file which is assumed to be the latest archive.
        Returns a tuple of the form (absoluteFilePath, modificationTimestamp) or None
        """
        if FileUtils.isValidDir(sourceDir):
            fileMTime = dict()
            for dirpath, dirnames, filenames in os.walk(sourceDir):
                for filename in filenames:
                    fileMTime[filename] = os.path.getmtime(os.path.join(dirpath, filename))

            fileMTimeTuple = max(fileMTime.items(), key=operator.itemgetter(1))

            return (os.path.join(sourceDir, fileMTimeTuple[0]), fileMTimeTuple[1])

    @staticmethod
    def isValidFile(path):
        if not os.path.isfile(path):
            logging.error("Provided path is not a valid file path.(" + path + ")")
            return False
        return True

    @staticmethod
    def isValidDir(path):
        if not os.path.isdir(path):
            logging.error("Provided path is not a valid dir path.(" + path + ")")
            return False
        return True

class FileUtilsError(Exception):
    """
    Abstract configuration exception.
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)