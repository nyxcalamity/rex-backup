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

import os, sys, shutil
import datetime, logging
from xml.dom.minidom import parse
from shutil import make_archive

from config import Config

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
        #TODO:consider replacing with tempfile.gettempdir()
        tmpDir = FileUtils.getWorkingDir() + FileUtils.getSep() + "tmp"
        if not os.path.exists(tmpDir):
            os.makedirs(tmpDir)
        return tmpDir

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
        """
        #TODO:add xml config validation
        dom = parse(FileUtils.getWorkingDir() + FileUtils.getSep() + "resources" + FileUtils.getSep() + fileName)

        #Check if there is anything at all
        if dom.getElementsByTagName("backup").length < 0:
            #TODO:think of a more elegant way to do this
            logging.error("No backup configuration found. Please check config xml file format and/or content.")
            raise SystemExit #Nothing to do here

        #Filling in config values from xml ET
        config = Config()
        backup = dom.getElementsByTagName("backup")[0]
        if backup.hasAttribute("archive"):config.archive = backup.getAttribute("archive")
        if backup.hasAttribute("backup-downtime"): config.backupDowntime = backup.getAttribute("backup-downtime")
        if backup.hasAttribute("rotation-period"): config.rotationPeriod = backup.getAttribute("rotation-period")
        config.source = backup.getElementsByTagName("source")[0].childNodes[0].data
        config.target = backup.getElementsByTagName("target")[0].childNodes[0].data

        return config

    @staticmethod
    def archive(source):
        """
        Performs an archiving operation on the source (both file and dir) and stores the archive in the working_dir/tmp.

        Returns:
        Absolute path to the archived file.
        """
        sourceName = os.path.basename(source) #Extracts base name
        archiveName = sourceName + "-" + datetime.datetime.now().strftime("%Y%M%d%H%M")
        return make_archive(FileUtils.getTmpDir() + FileUtils.getSep() + archiveName, 'gztar', source)

    @staticmethod
    def copy(sourceFile, targetDir):
        """
        Copies source file to the target dir.

        Returns:
        Absolute path to the target file.
        """
        if not os.path.exists(sourceFile):
            logging.error("Provided path doesn't exist.")
        if os.path.isdir(sourceFile):
            logging.error("Provided path is not a file path.")
        if not os.path.exists(targetDir):
            logging.warning("Provided path doesn't exist. Trying to create it.")
            try:
                os.makedirs(targetDir)
                logging.info("Created: " + targetDir)
            except Exception:
                logging.error("Couldn't create: " + targetDir)
        if os.path.isfile(targetDir):
            logging.error("Provided path is not a directory.")

        targetFile = targetDir + FileUtils.getSep() + os.path.basename(sourceFile)
        return shutil.copyfile(sourceFile, targetFile)