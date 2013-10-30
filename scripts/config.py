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

class BackupConfig:
    """
    Contains backup configuration parameters.
    """
    def __init__(self, checkerCfg=None, source=None, target=None, backupDowntime='0', rotationPeriod=None, performChecks=True,
                 performTmpCleanup=True):
        self.source = source
        self.target = target
        self.backupDowntime = backupDowntime
        self.rotationPeriod = rotationPeriod
        self.performChecks = performChecks
        self.performTmpCleanup = performTmpCleanup
        self.checkerCfg = checkerCfg

    def __str__(self):
        return self.__class__.__name__+"[source="+str(self.source)+",target="+str(self.target)+"]"

class CheckerConfig:
    """
    Contains backup checker configuration parameters.
    """
    def __init__(self, reporter=None, sendReports=True):
        self.reporter = reporter
        self.sendReports = sendReports

class ReporterConfig:
    """
    Contains reporter configuration parameters.
    """
    def __init__(self, fromAddress=None, toAddresses=None, subjectPrefix='', smtpCfg=None):
        self.fromAddress = fromAddress
        self.toAddresses = toAddresses
        self.subjectPrefix = subjectPrefix
        self.smtpCfg = smtpCfg

class SmtpConfig:
    """
    Contains smtp configuration parameters.
    """
    def __init__(self, host=None, port=None, username=None, password=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password