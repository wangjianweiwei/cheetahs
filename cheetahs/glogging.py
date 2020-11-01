# -*- coding: utf-8 -*-
"""
@Author: 王剑威
@Time: 2020/11/1 4:55 下午
"""
import os
import sys
import time
import socket
import logging
from logging.config import dictConfig, fileConfig
from threading import Lock

from cheetahs.util import check_is_writeable

SYSLOG_FACILITIES = {
    "auth": 4,
    "authpriv": 10,
    "cron": 9,
    "daemon": 3,
    "ftp": 11,
    "kern": 0,
    "lpr": 6,
    "mail": 2,
    "news": 7,
    "security": 4,  # DEPRECATED
    "syslog": 5,
    "user": 1,
    "uucp": 8,
    "local0": 16,
    "local1": 17,
    "local2": 18,
    "local3": 19,
    "local4": 20,
    "local5": 21,
    "local6": 22,
    "local7": 23
}

CONFIG_DEFAULTS = dict(
    version=1,
    disable_existing_loggers=False,

    root={"level": "INFO", "handlers": ["console"]},
    loggers={
        "gunicorn.error": {
            "level": "INFO",
            "handlers": ["error_console"],
            "propagate": True,
            "qualname": "gunicorn.error"
        },

        "gunicorn.access": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": True,
            "qualname": "gunicorn.access"
        }
    },
    handlers={
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": "ext://sys.stdout"
        },
        "error_console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": "ext://sys.stderr"
        },
    },
    formatters={
        "generic": {
            "format": "%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter"
        }
    }
)


def loggers():
    """ get list of all loggers """
    root = logging.root
    existing = root.manager.loggerDict.keys()
    return [logging.getLogger(name) for name in existing]


def parse_syslog_address(addr):
    # unix domain socket type depends on backend
    # SysLogHandler will try both when given None
    if addr.startswith("unix://"):
        sock_type = None

        # set socket type only if explicitly requested
        parts = addr.split("#", 1)
        if len(parts) == 2:
            addr = parts[0]
            if parts[1] == "dgram":
                sock_type = socket.SOCK_DGRAM

        return sock_type, addr.split("unix://")[1]

    if addr.startswith("udp://"):
        addr = addr.split("udp://")[1]
        socktype = socket.SOCK_DGRAM
    elif addr.startswith("tcp://"):
        addr = addr.split("tcp://")[1]
        socktype = socket.SOCK_STREAM
    else:
        raise RuntimeError("invalid syslog address")

    if '[' in addr and ']' in addr:
        host = addr.split(']')[0][1:].lower()
    elif ':' in addr:
        host = addr.split(':')[0].lower()
    elif addr == "":
        host = "localhost"
    else:
        host = addr.lower()

    addr = addr.split(']')[-1]
    if ":" in addr:
        port = addr.split(':', 1)[1]
        if not port.isdigit():
            raise RuntimeError("%r is not a valid port number." % port)
        port = int(port)
    else:
        port = 514

    return socktype, (host, port)


class Logger(object):
    LOG_LEVELS = {
        "critical": logging.CRITICAL,
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG
    }

    loglevel = logging.INFO
    syslog_fmt = "[%(process)d] %(message)s"
    access_fmt = "%(message)s"
    error_fmt = r"%(asctime)s [%(process)d] [%(levelname)s] %(message)s"
    datefmt = r"[%Y-%m-%d %H:%M:%S %z]"

    def __init__(self, cfg):
        self.error_log = logging.getLogger("cheetahs.error")
        self.error_log.propagate = False
        self.access_log = logging.getLogger("cheetahs.access")
        self.access_log.propagate = False
        self.error_handlers = []
        self.access_handlers = []
        self.logfile = None
        self.lock = Lock()
        self.cfg = cfg

        self.setup()

    def setup(self):
        self.loglevel = self.LOG_LEVELS.get(self.cfg.loglevel.lower(), logging.INFO)
        self.error_log.setLevel(self.loglevel)
        self.access_log.setLevel(logging.INFO)

        if self.cfg.capture_output and self.cfg.errorlog != "-":
            for stream in sys.stdout, sys.stderr:
                stream.flush()

            os.dup2(self.logfile.fileno(), sys.stdout.fileno())
            os.dup2(self.logfile.fileno(), sys.stderr.fileno())

        self._set_handler(self.error_log, self.cfg.errorlog, fmt=logging.Formatter(self.error_fmt, self.datefmt))

        if self.cfg.accesslog is not None:
            self._set_handler(self.access_log, self.cfg.accesslog, fmt=logging.Formatter(self.access_fmt),
                              stream=sys.stdout)

            # set syslog handler
            if self.cfg.syslog:
                self._set_syslog_handler(self.error_log, self.cfg, self.syslog_fmt, "error")
                if not self.cfg.disable_redirect_access_to_syslog:
                    self._set_syslog_handler(self.access_log, self.cfg, self.syslog_fmt, "access")

            if self.cfg.logconfig_dict:
                config = CONFIG_DEFAULTS.copy()
                config.update(self.cfg.logconfig_dict)
                try:
                    dictConfig(config)
                except (AttributeError, ImportError, ValueError, TypeError) as exc:
                    raise RuntimeError(str(exc))
            elif self.cfg.logconfig:
                if os.path.exists(self.cfg.logconfig):
                    defaults = CONFIG_DEFAULTS.copy()
                    defaults['__file__'] = self.cfg.logconfig
                    defaults['here'] = os.path.dirname(self.cfg.logconfig)
                    fileConfig(self.cfg.logconfig, defaults=defaults, disable_existing_loggers=False)
                else:
                    msg = "Error: log config '%s' not found"
                    raise RuntimeError(msg % self.cfg.logconfig)

    def _set_handler(self, log, output, fmt, stream=None):
        # 删除以前的gunicorn日志handler
        handler = self._get_gunicorn_handler(log)
        if handler:
            log.handlers.remove(handler)

        if output is not None:
            if output == "-":
                handler = logging.StreamHandler(stream)
            else:
                check_is_writeable(output)
                handler = logging.FileHandler(output)
                try:
                    os.chown(handler.baseFilename, self.cfg.user, self.cfg.group)
                except OSError:
                    # it's probably OK there, we assume the user has given
                    # /dev/null as a parameter.
                    pass
            handler.setFormatter(fmt)
            handler._gunicorn = True
            log.addHandler(handler)

    @staticmethod
    def _set_syslog_handler(log, cfg, fmt, name):
        # setup format
        if not cfg.syslog_prefix:
            prefix = cfg.proc_name.replace(":", ".")
        else:
            prefix = cfg.syslog_prefix

        prefix = "gunicorn.%s.%s" % (prefix, name)

        # set format
        fmt = logging.Formatter(r"%s: %s" % (prefix, fmt))

        # syslog facility
        try:
            facility = SYSLOG_FACILITIES[cfg.syslog_facility.lower()]
        except KeyError:
            raise RuntimeError("unknown facility name")

        # parse syslog address
        socktype, addr = parse_syslog_address(cfg.syslog_addr)

        # finally setup the syslog handler
        h = logging.handlers.SysLogHandler(address=addr, facility=facility, socktype=socktype)

        h.setFormatter(fmt)
        h._gunicorn = True
        log.addHandler(h)

    @staticmethod
    def _get_gunicorn_handler(log):
        for handler in log.handlers:
            if getattr(handler, "_gunicorn", False):
                return handler

    def critical(self, msg, *args, **kwargs):
        self.error_log.critical(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.error_log.error(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.error_log.warning(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.error_log.info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.error_log.debug(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self.error_log.exception(msg, *args, **kwargs)

    def log(self, lvl, msg, *args, **kwargs):
        if isinstance(lvl, str):
            lvl = self.LOG_LEVELS.get(lvl.lower(), logging.INFO)
        self.error_log.log(lvl, msg, *args, **kwargs)

    @staticmethod
    def now():
        """ return date in Apache Common Log Format """
        return time.strftime('[%d/%b/%Y:%H:%M:%S %z]')

    def reopen_files(self):
        if self.cfg.capture_output and self.cfg.errorlog != "-":
            for stream in sys.stdout, sys.stderr:
                stream.flush()

            with self.lock:
                if self.logfile is not None:
                    self.logfile.close()
                self.logfile = open(self.cfg.errorlog, 'a+')
                os.dup2(self.logfile.fileno(), sys.stdout.fileno())
                os.dup2(self.logfile.fileno(), sys.stderr.fileno())

        for log in loggers():
            for handler in log.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.acquire()
                    try:
                        if handler.stream:
                            handler.close()
                            handler.stream = handler._open()
                    finally:
                        handler.release()
