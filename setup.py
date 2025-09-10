"""
# -*- coding: utf-8 -*-
# ===============================================================================
#
# Copyright (C) 2013/2022 Laurent Labatut / Laurent Champagnac
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

from setuptools import find_packages, setup

# ===========================
# SETUP
# ===========================

p_name = "knockdaemon2"
p_author = "Laurent Champagnac / Laurent Labatut"
p_email = "champagnac.laurent@gmail.com"
p_url = "https://github.com/champax/knockdaemon2"

p_version = "3.13.0"


setup(

    # Project details
    name=p_name,
    author=p_author,
    author_email=p_email,
    url=p_url,
    description=p_name,

    # Version, format : Major.Minor.Revision
    version=p_version,

    # Packages
    packages=find_packages(exclude=["*_test*", "_*"]),
    include_package_data=True,

    # License & read me
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",

    # Data files
    data_files=[
        ("", ["requirements_test.txt", "requirements.txt", "README.md", "LICENSE.md"]),
    ],

    # Classifiers
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries",
        "Natural Language :: English",
    ],

    # Zip
    zip_safe=False,
)
