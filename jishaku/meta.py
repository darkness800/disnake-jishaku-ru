# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

from collections import namedtuple

import pkg_resources

__all__ = (
    '__author__',
    '__copyright__',
    '__docformat__',
    '__license__',
    '__title__',
    '__version__',
    'version_info'
)

# pylint: disable=invalid-name
VersionInfo = namedtuple('VersionInfo', 'major minor micro releaselevel serial')
version_info = VersionInfo(major=1, minor=6, micro=0, releaselevel='final', serial=0)

__author__ = 'Darkness800'
__copyright__ = 'Copyright 2021 Devon (Gorialis) R, Translated By darkness.py'
__docformat__ = 'restructuredtext ru'
__license__ = 'MIT'
__title__ = 'jishaku'
__version__ = '.'.join(map(str, (version_info.major, version_info.minor, version_info.micro)))

# Это гарантирует, что когда Джишаку перезагружен, pkg_resources требует, чтобы она предоставила правильную информацию о версии
pkg_resources.working_set.by_key.pop('jishaku', None)
