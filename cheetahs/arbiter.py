# -*- coding: utf-8 -*-
"""
@Author: 王剑威
@Time: 2020/10/31 3:33 下午
"""
import os

from cheetahs import SERVER_SOFTWARE


class Arbiter(object):

    def __init__(self, app):
        # 设置环境变量
        os.environ["SERVER_SOFTWARE"] = SERVER_SOFTWARE
        self._num_workers = None
        self._last_logged_active_worker_count = None
        self.log = None
        self.app = None
        self.cfg = None
        self.worker_class = None
        self.address = None

        self.setup(app)

        self.pidfile = None
        self.systemd = False
        self.worker_age = 0
        self.reexec_pid = 0
        self.master_pid = 0
        self.master_name = "Master"

    def setup(self, app):
        self.app = app
        self.cfg = app.cfg

        if self.log is None:
            self.log = self.cfg.logger_class(app.cfg)

        if "GUNICORN_FD" in os.environ:
            self.log.reopen_files()

        self.worker_class = app.cfg.worker_class
        self.address = app.cfg.address

    def run(self):
        pass
