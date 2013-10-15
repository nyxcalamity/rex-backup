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
from xml.dom.minidom import parse

from config import Config
from config import ConfigError

class FileUtils:
    """
    Provides major file operations like archiving, directory tree listing, config parsing and etc.
    """
    @staticmethod
    def readConfig(fileName):
        """
        Tries to parse a config file located in file working_directory/resources/fileName
        """
        #TODO:add xml config validation
        dom = parse(os.getcwd() + "/resources/" + fileName)

        #Check if there is anything at all
        if dom.getElementsByTagName("backup").length < 0:
            raise ConfigError("No backup configuration found. Please check config xml format and/or content.")

        #Filling in config values from xml ET
        config = Config()
        backup = dom.getElementsByTagName("backup")[0]
        if backup.hasAttribute("archive"):config.archive = backup.getAttribute("archive")
        if backup.hasAttribute("backup-downtime"): config.backupDowntime = backup.getAttribute("backup-downtime")
        if backup.hasAttribute("rotation-period"): config.rotationPeriod = backup.getAttribute("rotation-period")
        config.source = backup.getElementsByTagName("source")[0].childNodes[0].data
        config.target = backup.getElementsByTagName("target")[0].childNodes[0].data

        return config