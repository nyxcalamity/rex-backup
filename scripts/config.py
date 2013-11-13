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

class RexConfig:
    """
    Contains script configuration parameters.
    """
    def __init__(self, reporterConfig=None, backups=None, rotationPeriod=None, performChecks=True, performReporting=False):
        self.backups=backups
        self.rotationPeriod = rotationPeriod
        self.performChecks = performChecks
        self.performReporting = performReporting
        self.reporterConfig = reporterConfig

class BackupConfig:
    """
    Contains backup configuration parameters.
    """
    def __init__(self, source=None, target=None, backupDowntime='0', excludeRegexp = ''):
        self.source = source
        self.target = target
        self.excludeRegexp= excludeRegexp
        self.backupDowntime = backupDowntime

    def __str__(self):
        return self.__class__.__name__+"[source="+str(self.source)+",target="+str(self.target)+",downtime="+str(self.backupDowntime) +"]"

class ReporterConfig:
    """
    Contains reporter configuration parameters.
    """
    def __init__(self, fromAddress=None, toAddress=None, subjectPrefix='', smtpConfig=None):
        self.fromAddress = fromAddress
        self.toAddress = toAddress
        self.subjectPrefix = subjectPrefix
        self.smtpConfig = smtpConfig

class SmtpConfig:
    """
    Contains smtp configuration parameters.
    """
    def __init__(self, host=None, port=None, username=None, password=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password


def readConfig(configFilePath):
    """
    Parses provided config file and returns RexConfig object read from file.
    """
    dom = parse(configFilePath)

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
            if backup.hasAttribute("exclude-regexp"): backupCfg.excludeRegexp = str(backup.getAttribute("exclude-regexp"))
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
        raise ConfigError("Invalid file format.")

    return rexConfig

class ConfigError(Exception):
     """
     Abstract configuration error.
     """
     def __init__(self, value):
         self.value = value
     def __str__(self):
         return repr(self.value)