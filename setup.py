"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2017 Laurent Labatut / Laurent Champagnac
#
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
# ===============================================================================
"""

from distutils.core import setup

import re
from setuptools import find_packages


# ===========================
# TOOLS
# ===========================

def requirement_read(req_file):
    """
    Doc
    :param req_file: Doc
    :return: Doc
    """
    req_list = list()
    for rowBuffer in open(req_file).readlines():
        # Skip empty
        if len(rowBuffer.strip()) == 0:
            continue
            # Skip "- ..."
        if re.match("^-", rowBuffer):
            continue
            # Skip "# ..."
        if re.match("^#", rowBuffer):
            continue

        # Ok
        req_list.append(rowBuffer)
    return req_list


# ===========================
# SETUP
# ===========================

p_name = "knockdaemon2"
p_author = "Laurent Champagnac / Laurent Labatut"
p_email = "undisclosed@undisclosed.com"
p_url = "https://knock.center"

p_version = "0.0.1.dev0"


def entry_point_resolv():
    """


    :return:
    """
    ep = {
        'console_scripts': [
            'knockdaemon2 = knockdaemon2.Daemon.knockdaemon2:run',
            'knockautoupdate2 = knockdaemon2.Cron.AutoUpdate:cron'
        ]
    }

    return ep


def data_file_resolv():
    """
    :return:
    """
    datafile = [("",
                 [
                     "requirements_test.txt", "requirements.txt", "README.txt", "LICENSE.txt",
                 ])]

    return datafile


setup(

    # Project details
    name=p_name,
    author=p_author,
    author_email=p_email,
    url=p_url,
    description=p_name + " APIs",

    # Version, format : Major.Minor.Revision
    version=p_version,

    # Packages
    packages=find_packages(exclude=["*_test*", "_*"]),
    include_package_data=True,

    # License & read me
    license=open("LICENSE.txt").read(),
    long_description=open("README.txt").read(),

    # Data files
    data_files=data_file_resolv(),

    # Classifiers
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "License :: GPLv2",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Libraries",
    ],

    # Dependencies
    install_requires=requirement_read("requirements.txt"),

    # Dependencies : test
    tests_require=requirement_read("requirements_test.txt"),

    # Entry points
    entry_points=entry_point_resolv(),

    # Disable egg zip format
    zip_safe=False,
)
