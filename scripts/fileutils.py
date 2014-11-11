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

from shutil import make_archive


class FileUtilsError(Exception):
     """
     Abstract file utils error.
     """
     def __init__(self, value):
         self.value = value
     def __str__(self):
         return repr(self.value)

fileErrorMsg = "Provided path does not exist or is not a file: "
dirErrorMsg = "Provided path does not exist or is not a directory: "

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
    tmpDir = os.path.join(getTmpDir(), "local")
    if not os.path.exists(tmpDir):
        os.makedirs(tmpDir)
    return tmpDir

def getTmpRemoteDir():
    """
    Returns path to the temporary directory. Creates one if it didn't exist.
    """
    tmp_dir = os.path.join(getTmpDir(), "remote")
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    return tmp_dir

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
    shutil.rmtree(getTmpRemoteDir())

def archiveDir(dirPath, archiveType):
    """
    Performs an archiving operation on the dirPath and stores the archive in the #getTmpLocalDir(). Returns an absolute
    path to the archive file.
    """
    if os.path.isdir(dirPath):
        sourceName = os.path.basename(dirPath) #Extracts base name
        archiveName = sourceName + "-" + datetime.datetime.now().strftime("%Y%m%d%H%M")
        return make_archive(os.path.join(getTmpLocalDir(), archiveName), archiveType, dirPath)
    else:
        raise FileUtilsError(dirErrorMsg + dirPath)

def generateMD5File(filePath):
    """
    Generates an md5 code for a file and returns the absolute path to the generated file.
    """
    if os.path.isfile(filePath):
        md5Str = filePath + "-" + str(time.time())
        #Apparently md5 algorithm operates on bytes, that's why we need to encode the string
        m = hashlib.md5(md5Str.encode("utf-8"))
        md5File = open(filePath+".md5","w")
        md5File.write(m.hexdigest() + "\t" + os.path.basename(filePath))
        md5File.close()
        return md5File.name
    else:
        raise FileUtilsError(fileErrorMsg + filePath)

def copyFile(filePath, dirPath):
    """
    Copies source file to the target dir. Returns absolute path to the target file or none.
    """
    if os.path.isfile(filePath):
        if not os.path.isdir(dirPath):
            try:
                os.makedirs(dirPath)
                logging.info("Created a directory: " + dirPath)
            except Exception as ex:
                raise FileUtilsError("Copy destination can't be reached. Couldn't create directory: " + dirPath + \
                                     ". Reason: " + ex.__str__())

        targetFile = os.path.join(dirPath , os.path.basename(filePath))
        shutil.copyfile(filePath, targetFile)
        return targetFile
    else:
        raise FileUtilsError(fileErrorMsg + filePath)

def removeFile(filePath):
    """
    Removes a file from the FS. Returns True if succeeded and False otherwise.
    """
    if os.path.isfile(filePath):
        os.remove(filePath)
        return True
    else:
        return False

def getFiles(dirPath, pattern=""):
    """
    Searches dirPath and its subdirectories for files. File names are optionally checked against regexp pattern.
    """
    if os.path.isdir(dirPath):
        archives = []
        for dirpath, dirnames, filenames in os.walk(dirPath):
            for filename in filenames:
                if re.search(pattern, filename):
                    archives.append(os.path.join(dirpath, filename))
        return archives
    else:
        raise FileUtilsError(dirErrorMsg + dirPath)

def compareArchiveAgainstDir(archiveFilePath, sourceDirPath, exclude_regexp="", ignoreLinks=True):
    """
    Traverses sourceDirPath and tries to find matches in the archive. Returns a list of inconsistencies or None.
    """
    #TODO:determine read mode automatically as well as tar vs zip file
    if not archiveFilePath.endswith("tar.gz"):
        raise NotImplementedError("Only tar.gz archives are supported at the moment")

    archiveFile = tarfile.open(archiveFilePath, "r:gz")
    tarMembers = dict()
    for member in archiveFile.getmembers():
        tarMembers[member.name] = member.mtime

    srcMembers = dict()
    for dirpath, dirnames, filenames in os.walk(sourceDirPath):
        for filename in filenames:
            fileAbsolutePath = os.path.join(dirpath, filename)
            if ignoreLinks and not os.path.islink(fileAbsolutePath):
                srcMembers[fileAbsolutePath] = os.path.getmtime(fileAbsolutePath)
        for dirname in dirnames:
            dirAbsolutePath = os.path.join(dirpath, dirname)
            if ignoreLinks and not os.path.islink(dirAbsolutePath):
                srcMembers[dirAbsolutePath] = os.path.getmtime(dirAbsolutePath)

    inconsistencies = []
    for srcKey in srcMembers:
        tarKey = srcKey.replace(sourceDirPath, ".")
        altTarKey = tarKey + os.path.sep

        #determine which key is used
        key = tarKey if tarKey in tarMembers else altTarKey
        if not re.search(exclude_regexp, key):
            if key != tarKey and not (key in tarMembers):  # don't perform double checks
                inconsistencies.append("Can't find key in the archive: " + tarKey)
            elif datetime.date.fromtimestamp(srcMembers[srcKey]) != datetime.date.fromtimestamp(tarMembers[key]):
                inconsistencies.append("Wrong modification time detected: key=" + tarKey + ";archiveMtime=" + \
                                       timestampToStr(tarMembers[tarKey]) + ";srcMtime=" + timestampToStr(srcMembers[srcKey]))

    if len(inconsistencies) > 0:
        return inconsistencies

def timestampToStr(timestamp):
    """
    Gets a timestamp and creates a formatted date string out of that timestamp.
    """
    return datetime.date.fromtimestamp(timestamp).strftime("%Y-%m-%d-%H:%M")