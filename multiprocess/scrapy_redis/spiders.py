#!/usr/bin/env python
# -*- coding: utf-8 -*-
import threading
import time
from multiprocessing import Process

import psutil
import pymongo
import redis
from scrapy.crawler import CrawlerProcess
from scrapy.http import Request
from scrapy_redis.spiders import RedisSpider
from scrapy_redis.utils import bytes_to_str
from tqdm import tqdm


class JiChengSpider(RedisSpider):

    @classmethod
    def from_crawler(self, crawler, *args, **kwargs):
        obj = super(JiChengSpider, self).from_crawler(crawler, *args, **kwargs)
        return obj

    def make_request_from_data(self, data):
        data = bytes_to_str(data, self.redis_encoding)
        data = eval(data)
        self.logger.debug(data)
        return Request(url=data["url"], meta=data["meta"], dont_filter=True)


class ThreadMonitor(threading.Thread):
    def __init__(self, redis_key, interval=1, bar_name=None):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.setting = get_project_settings()
        self.redis = get_redis_from_settings(self.setting)
        self.redis_key = redis_key
        self.total = self.redis.scard(self.redis_key)
        self.interval = interval
        if bar_name:
            self.bar_name = bar_name
        else:
            self.bar_name = self.redis_key
        self.stop = False

    def run(self):
        with tqdm(total=self.total, desc=self.bar_name) as pbar:
            last_size = self.total
            while not self.stop:
                end = time.time() + self.interval
                current_size = self.redis.scard(self.redis_key)
                pbar.update(last_size - current_size)
                if time.time() < end:
                    time.sleep(end - time.time())
                last_size = current_size
                if current_size == 0:
                    self.stop = True


class ThreadWriter(threading.Thread):
    def __init__(self, redis_key, interval=1, bar_name=None, buffer_size=512):
        threading.Thread.__init__(self)
        self.stop = False
        self.interval = interval
        self.buffer_size = buffer_size
        self.counter = 0
        self.setting = get_project_settings()
        self.redis = get_redis_from_settings(self.setting)
        self.redis_key = redis_key
        self.total = self.redis.llen(self.redis_key)
        if bar_name:
            self.bar_name = bar_name
        else:
            self.bar_name = self.redis_key

    def write(self, item):
        raise NotImplementedError

    def flush(self):
        raise NotImplementedError

    def setup(self):
        pass

    def cleanup(self):
        pass

    def run(self):
        with tqdm(total=self.total, desc=self.bar_name) as pbar:
            retries = 30
            while not self.stop:
                current_element = self.redis.lpop(self.redis_key)
                if current_element:
                    pbar.update(1)
                    self.write(current_element)
                    retries = 30
                else:
                    retries = retries - 1
                    time.sleep(1)
                if retries <= 0:
                    self.stop = True
            self.flush()
            self.cleanup()


class ThreadFileWriter(ThreadWriter):
    def __init__(self, redis_key, out_file, table_header, interval=1, bar_name=None, buffer_size=32):
        super(ThreadFileWriter, self).__init__(redis_key=redis_key, interval=interval, bar_name=bar_name, buffer_size=buffer_size)
        self.out_file = out_file
        self.out = open(self.out_file, "w")
        self.table_header = table_header
        self.out.write("\t".join(self.table_header) + "\n")
        self.buffer = []

    def stop(self):
        self.stop = True

    def write(self, item):
        self.counter = self.counter + 1
        item = eval(item)
        self.buffer.append(item)
        if self.counter % self.buffer_size == 0:
            self.counter = 0
            values = []
            for item in self.buffer:
                value = ""
                for key in self.table_header:
                    if key in item:
                        if value:
                            value = value + "\t" + str(item[key])
                        else:
                            value = str(item[key])
                    else:
                        value = value + "\t" + "NA"
                if value:
                    values.append(value)
            #values = ["\t".join([str(item[key]) for key in self.table_header]) for item in self.buffer]
            self.out.write("\n".join(values) + "\n")
            self.buffer = []

    def flush(self):
        if self.buffer:
            #values = ["\t".join([str(item[key]) for key in self.table_header]) for item in self.buffer]
            values = []
            for item in self.buffer:
                value = ""
                for key in self.table_header:
                    if key in item:
                        if value:
                            value = value + "\t" + str(item[key])
                        else:
                            value = str(item[key])
                    else:
                        value = value + "\t" + "NA"
                if value:
                    values.append(value)
            self.out.write("\n".join(values) + "\n")

    def cleanup(self):
        self.out.close()


class ThreadMongoWriter(ThreadWriter):
    def __init__(self, redis_key, out_mongo_url, collection, interval=1, bar_name=None, buffer_size=512):
        super(ThreadMongoWriter, self).__init__(redis_key=redis_key, interval=interval, bar_name=bar_name, buffer_size=buffer_size)
        self.db = pymongo.MongoClient(out_mongo_url)
        self.out = self.db[collection]
        self.buffer = []

    def stop(self):
        self.stop = True

    def write(self, item):
        self.counter = self.counter + 1
        self.buffer.append(item)
        if self.counter % self.buffer_size == 0:
            self.out.insert_many(self.buffer)
            self.buffer = []
            self.counter = 0

    def flush(self):
        if self.buffer:
            self.out.insert_many(self.buffer)

    def cleanup(self):
        self.db.close()


from scrapy.cmdline import execute
from scrapy_redis.connection import (
    from_settings,
    get_redis,
    get_redis_from_settings,
)
from scrapy.utils.project import get_project_settings

from scrapy_redis.connection import get_redis_from_settings

import logging


class ClusterRunner(object):
    def __init__(self, spider_name, thread_writer=None, spider_num=psutil.cpu_count(logical=True)):
        self.spider_name = spider_name
        self.spider_num = spider_num
        self.start_urls_redis_key = "%(name)s:start_urls" % {"name": self.spider_name}
        self.items_redis_key = "%(name)s:items" % {"name": self.spider_name}
        self.setting = get_project_settings()
        self.logger = self.get_loger()
        self.redis = get_redis_from_settings(self.setting)
        self.redis = redis.Redis(host='192.168.0.117', port=6379, db=0)
        self.logger.info(self.redis)

    def get_loger(self):
        log_config = {}
        parmer_map = {"LOG_LEVEL":"level","LOG_FILE":"filename","LOG_FORMAT":"format"}
        for key in self.setting:
            if key in parmer_map:
                log_config[parmer_map[key]] = self.setting[key]
        logging.basicConfig(**log_config)
        return logging.getLogger(__name__)

    def get_thread_writer(self):
        return None

    def get_thread_monitor(self):
        return None

    @classmethod
    def run_spider(cls, spider_name):
        from scrapy.cmdline import execute
        execute(['scrapy', 'crawl', spider_name])

    def init_start_urls(self):
        raise NotImplementedError

    def run(self):
        if self.spider_num <= 0:
            return
        #初始化种子URL
        self.init_start_urls()
        #开启监控线程
        self.thread_monitor = self.get_thread_monitor()
        if self.thread_monitor:
            self.thread_monitor.start()
            self.logger.info("start monitor success !")

        #开启爬虫
        self.spider_list = []
        if self.spider_num > 1:
            process = CrawlerProcess(get_project_settings())
            for spider in ["shoujiguishudi"]*self.spider_num:
                process.crawl(spider)  # 根据爬虫名列表爬取
            process.start()
            # for i in range(self.spider_num):
            #     self.spider_list.append(Process(target=self.run_spider, name=self.spider_name + "-" + str(i), kwargs={"spider_name": self.spider_name}))
            # for p in self.spider_list:
            #     p.daemon = True
            #     p.start()
            # for p in self.spider_list:
            #     p.join()
        elif self.spider_num == 1:
            self.logger.info("mode : run in standalone !")
            self.run_spider(spider_name=self.spider_name)

        # 开启写线程
        self.thread_writer = self.get_thread_writer()
        if self.thread_writer:
            self.thread_writer.start()
            self.logger.info("start writer success !")
            self.thread_writer.join()
