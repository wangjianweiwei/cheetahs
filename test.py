# -*- coding: utf-8 -*-
"""
@Author: 王剑威
@Time: 2020/10/31 5:15 下午
"""

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-b")
parser.add_argument("args", nargs="*")

parser.parse_args(["-b", " 0.0.0.0:8000", "web:app"])
print(parser.parse_args())
