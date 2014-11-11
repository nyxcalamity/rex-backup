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


def get_working_dir():
    """
    Returns script working directory. (Parent directory of the script that invoked python interpreter)
    """
    return os.path.join(sys.path[0], os.pardir)


def get_tmp_dir():
    """
    Returns path to the temporary directory. Creates one if it didn't exist.
    """
    tmp_dir = os.path.join(get_working_dir(), "tmp")
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    return tmp_dir


def get_tmp_local_dir():
    """
    Returns path to the temporary directory. Creates one if it didn't exist.
    """
    tmp_dir = os.path.join(get_tmp_dir(), "local")
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    return tmp_dir


def get_tmp_remote_dir():
    """
    Returns path to the temporary directory. Creates one if it didn't exist.
    """
    tmp_dir = os.path.join(get_tmp_dir(), "remote")
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    return tmp_dir


def get_log_dir():
    """
    Returns path to the log directory. Creates one if it didn't exist.
    """
    log_dir = os.path.join(get_working_dir(), "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return log_dir


def clean_tmp():
    """
    Deletes all files in the temp directory.
    """
    shutil.rmtree(get_tmp_dir())
    shutil.rmtree(get_tmp_remote_dir())


def archive_dir(dir_path, archive_type):
    """
    Performs an archiving operation on the dirPath and stores the archive in the #get_tmp_local_dir(). Returns an absolute
    path to the archive file.
    """
    if os.path.isdir(dir_path):
        src_name = os.path.basename(dir_path)
        arc_name = src_name + "-" + datetime.datetime.now().strftime("%Y%m%d%H%M")
        return make_archive(os.path.join(get_tmp_local_dir(), arc_name), archive_type, dir_path)
    else:
        raise FileUtilsError(dirErrorMsg + dir_path)


def generate_md5_file(file_path):
    """
    Generates an md5 code for a file and returns the absolute path to the generated file.
    """
    if os.path.isfile(file_path):
        md5_str = file_path + "-" + str(time.time())
        #Apparently md5 algorithm operates on bytes, that's why we need to encode the string
        m = hashlib.md5(md5_str.encode("utf-8"))
        md5_file = open(file_path+".md5", "w")
        md5_file.write(m.hexdigest() + "\t" + os.path.basename(file_path))
        md5_file.close()
        return md5_file.name
    else:
        raise FileUtilsError(fileErrorMsg + file_path)


def copy_file(file_path, dir_path):
    """
    Copies source file to the target dir. Returns absolute path to the target file or none.
    """
    if os.path.isfile(file_path):
        if not os.path.isdir(dir_path):
            try:
                os.makedirs(dir_path)
                logging.info("Created a directory: " + dir_path)
            except Exception as ex:
                raise FileUtilsError("Copy destination can't be reached. Couldn't create directory: " + dir_path + \
                                     ". Reason: " + ex.__str__())

        target_file = os.path.join(dir_path , os.path.basename(file_path))
        shutil.copyfile(file_path, target_file)
        return target_file
    else:
        raise FileUtilsError(fileErrorMsg + file_path)


def remove_file(file_path):
    """
    Removes a file from the FS. Returns True if succeeded and False otherwise.
    """
    if os.path.isfile(file_path):
        os.remove(file_path)
        return True
    else:
        return False


def get_files(dir_path, pattern=""):
    """
    Searches dir_path and its subdirectories for files. File names are optionally checked against regexp pattern.
    """
    if os.path.isdir(dir_path):
        archives = []
        for dirpath, dirnames, filenames in os.walk(dir_path):
            for filename in filenames:
                if re.search(pattern, filename):
                    archives.append(os.path.join(dirpath, filename))
        return archives
    else:
        raise FileUtilsError(dirErrorMsg + dir_path)


def compare_archive_against_dir(archive_file_path, source_dir_path, exclude_regexp="", ignore_links=True):
    """
    Traverses source_dir_path and tries to find matches in the archive. Returns a list of inconsistencies or None.
    """
    #TODO:determine read mode automatically as well as tar vs zip file
    if not archive_file_path.endswith("tar.gz"):
        raise NotImplementedError("Only tar.gz archives are supported at the moment")

    archive_file = tarfile.open(archive_file_path, "r:gz")
    tar_members = dict()
    for member in archive_file.getmembers():
        tar_members[member.name] = member.mtime

    src_members = dict()
    for dirpath, dirnames, filenames in os.walk(source_dir_path):
        for filename in filenames:
            file_absolute_path = os.path.join(dirpath, filename)
            if ignore_links and not os.path.islink(file_absolute_path):
                src_members[file_absolute_path] = os.path.getmtime(file_absolute_path)
        for dirname in dirnames:
            dir_absolute_path = os.path.join(dirpath, dirname)
            if ignore_links and not os.path.islink(dir_absolute_path):
                src_members[dir_absolute_path] = os.path.getmtime(dir_absolute_path)

    inconsistencies = []
    for srcKey in src_members:
        tar_key = srcKey.replace(source_dir_path, ".")
        alt_tar_key = tar_key + os.path.sep

        #determine which key is used
        key = tar_key if tar_key in tar_members else alt_tar_key
        if not re.search(exclude_regexp, key):
            if key != tar_key and not (key in tar_members):  # don't perform double checks
                inconsistencies.append("Can't find key in the archive: " + tar_key)
            elif datetime.date.fromtimestamp(src_members[srcKey]) != datetime.date.fromtimestamp(tar_members[key]):
                inconsistencies.append("Wrong modification time detected: key=" + tar_key + ";archiveMtime=" + \
                                       timestamp2str(tar_members[tar_key]) + ";srcMtime=" + timestamp2str(src_members[srcKey]))

    if len(inconsistencies) > 0:
        return inconsistencies


def timestamp2str(timestamp):
    """
    Gets a timestamp and creates a formatted date string out of that timestamp.
    """
    return datetime.date.fromtimestamp(timestamp).strftime("%Y-%m-%d-%H:%M")