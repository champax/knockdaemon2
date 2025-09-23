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

import toml
from setuptools import find_packages, setup

# ===========================
# SETUP
# ===========================

with open("pyproject.toml", "r") as f:
    data_pyproject = toml.load(f)
p_name = data_pyproject['project']['name']
p_author = data_pyproject['project']['authors'][0]['name']
p_email = data_pyproject['project']['authors'][0]['email']
p_url = data_pyproject['project']['urls']['Repository']
p_version = data_pyproject['project']['version']

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
    classifiers=data_pyproject['project']['classifiers'],

    # Zip
    zip_safe=False,
)
