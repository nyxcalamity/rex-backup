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


from xml.dom.minidom import parse
import xml.dom.minidom as minidom
import os

from config import Context

class FileUtils:
    '''
        Class that provides major file operations like archiving, directory tree listing and etc.
    '''

    def __init__(self):
        pass

    @staticmethod
    def readXml2Obj(fileName):
        dom = parse(os.getcwd() + "/resources/" + fileName)
        backups = dom.getElementsByTagName("backup")
        context = Context()
        for backup in backups:
            if backup.hasAttribute("archive"):context.archive = backup.getAttribute("archive")
            if backup.hasAttribute("backup-downtime"): context.backupDowntime = backup.getAttribute("backup-downtime")
            if backup.hasAttribute("rotation-period"): context.rotationPeriod = backup.getAttribute("rotation-period")

            context.source = backup.getElementsByTagName("source")[0].childNodes[0].data
            context.target = backup.getElementsByTagName("target")[0].childNodes[0].data
        return context