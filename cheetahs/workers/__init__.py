# -*- coding: utf-8 -*-
"""
@Author: 王剑威
@Time: 2020/11/1 12:36 下午
"""

SUPPORTED_WORKERS = {
    "sync": "cheetahs.workers.sync.SyncWorker",
    "eventlet": "cheetahs.workers.geventlet.EventletWorker",
    "gevent": "cheetahs.workers.ggevent.GeventWorker",
    "gevent_wsgi": "cheetahs.workers.ggevent.GeventPyWSGIWorker",
    "gevent_pywsgi": "cheetahs.workers.ggevent.GeventPyWSGIWorker",
    "tornado": "cheetahs.workers.gtornado.TornadoWorker",
    "gthread": "cheetahs.workers.gthread.ThreadWorker",
}
