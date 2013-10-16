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

import os, sys, shutil, tempfile, datetime, logging
from xml.dom.minidom import parse
from shutil import make_archive

from config import Config
from config import ConfigError

class FileUtils:
    """
    Provides major file operations like archiving, directory tree listing, config parsing and etc.
    """

    @staticmethod
    def getSep():
        """
        Returns a platform specific path separator.
        """
        return os.sep

    @staticmethod
    def getWorkingDir():
        """
        Returns application working directory. (Parent directory of the script that invoked python interpreter)
        """
        #TODO:check if this works in windows
        return sys.path[0] + FileUtils.getSep() + os.pardir

    @staticmethod
    def getTmpDir():
        """
        Returns path to the temporary directory. Creates one if it didn't exist.
        """
        tmpDir =  FileUtils.getWorkingDir() + FileUtils.getSep() + "tmp"
        if not os.path.exists(tmpDir):
            os.makedirs(tmpDir)
        return tmpDir

    @staticmethod
    def cleanTmp():
        """
        Deletes all archives by ARCHIVE_PREFIX from temporary directory.
        """
        for file in os.listdir(FileUtils.getTmpDir()):
            os.remove(FileUtils.getTmpDir() + FileUtils.getSep() + file)

    @staticmethod
    def getLogDir():
        """
        Returns path to the log directory. Creates one if it didn't exist.
        """
        logDir = FileUtils.getWorkingDir() + FileUtils.getSep() + "logs"
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
        configFile = FileUtils.getWorkingDir() + FileUtils.getSep() + "resources" + FileUtils.getSep() + fileName
        if os.path.exists(configFile):
            dom = parse(configFile)

            #Filling in config values from xml ET
            config = Config()
            try:
                backup = dom.getElementsByTagName("backup")[0]
                if backup.hasAttribute("archive"):config.archive = backup.getAttribute("archive")
                if backup.hasAttribute("backup-downtime"): config.backupDowntime = backup.getAttribute("backup-downtime")
                if backup.hasAttribute("rotation-period"): config.rotationPeriod = backup.getAttribute("rotation-period")
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
    def archive(source):
        """
        Performs an archiving operation on the source (both file and dir) and stores the archive in the working_dir/tmp.

        Returns:
        Absolute path to the archived file.
        """
        sourceName = os.path.basename(source) #Extracts base name
        archiveName = sourceName + "-" + datetime.datetime.now().strftime("%Y%m%d%H%M")
        return make_archive(FileUtils.getTmpDir() + FileUtils.getSep() + archiveName, 'gztar', source)

    @staticmethod
    def copy(sourceFile, targetDir):
        """
        Copies source file to the target dir.

        Returns:Absolute path to the target file.
        Throws: FileUtilsError
        """
        errorMsg = ""
        if not os.path.exists(sourceFile):
            errorMsg = "Provided path doesn't exist."
        if not errorMsg and os.path.isdir(sourceFile):
            errorMsg = "Provided path is not a file path."
        if not errorMsg and not os.path.exists(targetDir):
            logging.warning("Provided path doesn't exist. Trying to create it.")
            try:
                os.makedirs(targetDir)
                logging.info("Created: " + targetDir)
            except Exception:
                errorMsg = "Couldn't create: " + targetDir + ". Target location can't be reached."
        if not errorMsg and os.path.isfile(targetDir):
            errorMsg = "Provided path is not a directory."

        if errorMsg:
            logging.error(errorMsg)
            raise FileUtilsError(errorMsg)

        targetFile = targetDir + FileUtils.getSep() + os.path.basename(sourceFile)
        shutil.copyfile(sourceFile, targetFile)
        return targetFile

class FileUtilsError(Exception):
    """
    Abstract configuration exception.
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)