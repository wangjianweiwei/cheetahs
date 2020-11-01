# -*- coding: utf-8 -*-
"""
@Author: 王剑威
@Time: 2020/10/31 3:39 下午
"""
import os
import sys

from cheetahs.arbiter import Arbiter
from cheetahs.config import Config, get_default_config_file


class BaseApplication(object):

    def __init__(self, usage=None, prog=None):
        self.usage = usage
        self.prog = prog
        self.cfg: Config = None
        self.callable = None
        self.logger = None
        self.app_uri = None
        self.do_load_config()

    def do_load_config(self):
        try:
            self.load_default_config()
            self.load_config()
        except Exception as e:
            print(f"\nError: {str(e)}", file=sys.stderr)
            sys.stderr.flush()
            sys.exit(1)

    def load_default_config(self):
        self.cfg = Config(self.usage, prog=self.prog)

    def load_config(self):
        raise NotImplementedError

    def init(self, parser, opts, args):
        raise NotImplementedError

    def run(self):
        Arbiter(self).run()


class Application(BaseApplication):

    def chdir(self):
        # 切到应用程序所在的目录
        os.chdir(self.cfg.chdir)

        # 将应用程序的目录加到python的包模块搜索路径列表中
        if self.cfg.chdir not in sys.path:
            sys.path.insert(0, self.cfg.chdir)

    def load_config(self):
        parser = self.cfg.parser()
        # 解析命令行上的配置
        args = parser.parse_args()

        cfg = self.init(parser, args, args.args)

        self.chdir()

        # 解析环境变量中的配置
        env_args = parser.parse_args(self.cfg.get_cmd_args_from_env())

        if args.config:
            self.load_config_from_file(args.config)
        elif env_args.config:
            self.load_config_from_file(env_args.config)
        else:
            default_config = get_default_config_file()
            if default_config:
                self.load_config_from_file(default_config)

    def load_config_from_file(self, path):
        pass

    def init(self, parser, opts, args):
        raise NotImplementedError


class WSGIApplication(Application):
    def init(self, parser, opts, args):
        if not args:
            parser.error("没有指定应用程序模块")

        # 更新应用程序模块路径的配置
        self.cfg.set("default_proc_name", args[0])
        self.app_uri = args[0]


if __name__ == '__main__':
    sys.argv = ["", "-b", " 0.0.0.0:8000", "web:app"]
    WSGIApplication()
