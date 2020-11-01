# -*- coding: utf-8 -*-
"""
@Author: 王剑威
@Time: 2020/10/31 3:32 下午
"""

version_info = (20, 0, 4)
__version__ = ".".join([str(v) for v in version_info])
SERVER_SOFTWARE = "gunicorn/%s" % __version__
