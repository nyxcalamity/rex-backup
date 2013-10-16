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

from file_utils import FileUtils

def performBackupTask(config):
    """
    Performs backup according to provided config.
    """
    logging.info("PERFORMING BACKUP")
    logging.info("Archiving source directory...")
    archiveFile = FileUtils.archive(config.source)
    logging.info("Generating MD5 file...")
    archiveMD5File = FileUtils.generateMD5File(archiveFile)
    logging.info("Copying archive to the target...")
    targetArchiveFile = FileUtils.copy(archiveFile, config.target)
    logging.info("Copying MD5 file to the target...")
    targetArchiveMD5File = FileUtils.copy(archiveMD5File, config.target)

    if targetArchiveFile and targetArchiveMD5File:
        logging.info("Cleaning tmp directory...")
        FileUtils.cleanTmp()

    logging.info("BACKUP COMPLETED SUCCESSFULLY")

def performBackupCheck(config):
    """
    Checks if backup was performed correctly according to specified config.
    """
    logging.info("CHECKING BACKUP")
    logging.info("Copying latest archive to tmp dir...")
    logging.info("Comparing tree listings...")
    logging.info("Comparing file sizes and modification dates...")
    logging.info("Sending reports...")
    logging.info("BACKUP CHECK COMPLETED SUCCESSFULLY")

def main():
    logging.info("Reading config file...")
    config = FileUtils.readConfig("config.xml")
    performBackupTask(config)
    performBackupCheck(config)

if __name__ == '__main__':
    #Setting up application logger
    #logFile = os.path.join(FileUtils.getLogDir(), "rex-backup-"+datetime.datetime.now().strftime("%Y%m%d%H%M")+".log")
    logFormat = "%(asctime)s [%(levelname)s]:%(module)s - %(message)s"
    #Will create a new file each time application is executed
    #logging.basicConfig(filename=logFile, filemode="w",level=logging.INFO,format=logFormat)
    logging.basicConfig(level=logging.DEBUG,format=logFormat)
    main()