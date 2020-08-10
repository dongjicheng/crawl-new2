#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from multiprocess.core.spider import SpiderManger, Seed
from multiprocess.core import HttpProxy
from multiprocess.tools import process_manger
import re
import sys
from multiprocess.tools import timeUtil
from mongo import op
from tqdm import tqdm
import time
from datetime import date
import json
import random
from fake_useragent import UserAgent


class SecooMonthJob(SpiderManger):
    def __init__(self, current_date, **kwargs):
        super(SecooMonthJob, self).__init__(**kwargs)
        self.proxies = list(map(lambda x: ("http://u{}:crawl@192.168.0.71:3128".format(x)), range(28)))
        self.ua = UserAgent()
        self.current_date = current_date
        self.current_date = current_date
        with op.DBManger() as m:
            total = m.count(db_collect=("secoo", "CleanListNew"))
            for pid, price in tqdm(m.read_from(db_collect=("secoo", "CleanListNew"), out_field=("pid", "price")),
                                   total=total, desc="reading"):
                self.seeds_queue.put(Seed((pid, price), kwargs["retries"], type=0))
        self.seed_retries = kwargs["retries"]
        self.page_pattern = re.compile(r'totalCurrCommentNum":.*?,')
        self.block_pattern = re.compile(r'{"isShow.*?}')
        self.bench = timeUtil.getdate(-90, format='%Y%m%d')
        self.log.info("bench: " + self.bench)
        self.id_pattern = re.compile(r'"id":\d+')
        self.pid_pattern = re.compile(r'productId":\d+')
        self.time_pattern = re.compile(r'createDate":\d+')
        self.user_pattern = re.compile(r'userName":".*?"')
        self.device_pattern = re.compile(r'sourceDevice":".*?"')

    def make_request(self, seed):
        url = 'https://las.secoo.com/api/comment/show_product_comment?filter=0&page=1' \
              '&pageSize=10&productBrandId=&productCategoryId=&productId={0}&type=0&callback=jsonp1'.format(seed.value[0])
        request = {"url": url,
                   "mothed": "get",
                   "proxies": {"http": random.choice(self.proxies)},
                   "headers": {"Connection": "close", "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36 Edge/17.17134'}}
        return request

    def parse_item(self, content, seed):
        pid, price = seed.value
        page = self.page_pattern.findall(content)
        if len(page) > 0:
            temp = page[0]
            totalpage = int(temp[21:len(temp) - 1])
            temp = int(totalpage / 10)
            if totalpage > temp * 10:
                pagecount = temp + 1
            else:
                pagecount = temp
        else:
            pagecount = 1
        result = []
        for pageid in range(1, pagecount + 1):
            url = 'https://las.secoo.com/api/comment/show_product_comment?filter=0&page={0}' \
                  '&pageSize=10&productBrandId=&productCategoryId=&productId={1}&type=0&callback=jsonp1'.format(pageid,pid)
            request = {"url": url,
                       "mothed": "get",
                       "proxies": {"http": random.choice(self.proxies)},
                       "headers": {"Connection": "close",
                                   "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36 Edge/17.17134'}}
            respone = self.do_request(request)
            content = respone.text

            pid_rel, price = seed.value
            block = self.block_pattern.findall(content)

            for item in block:
                cid = self.id_pattern.findall(item)
                if len(cid) > 0:
                    temp = cid[0]
                    cid = temp[5:len(temp)]
                else:
                    cid = 'NA'

                pid = self.pid_pattern.findall(item)
                if len(pid) > 0:
                    temp = pid[0]
                    pid = temp[11:len(temp)]
                else:
                    pid = 'NA'

                time2 = self.time_pattern.findall(item)
                if len(time2) > 0:
                    temp = time2[0]
                    time1 = temp[12:len(temp)]
                    datestr = date.fromtimestamp(float(time1) / 1000).strftime('%Y%m%d')
                else:
                    datestr = 'NoDate'

                user = self.user_pattern.findall(item)
                if len(user) > 0:
                    temp = user[0]
                    user = temp[11:len(temp) - 1]
                else:
                    user = 'NA'

                device = self.device_pattern.findall(item)
                if len(device) > 0:
                    temp = device[0]
                    device = temp[15:len(temp) - 1]
                else:
                    device = 'NA'
                if datestr != 'NoDate':
                    if (self.bench <= datestr):
                        result.append({"cid": cid, "pid_rel": pid_rel, "user": user, "device": device,
                                       "price": price, "date": datestr, "_date": self.current_date})
        if result:
            self.write(result)
            seed.ok()


if __name__ == "__main__":
    current_date = timeUtil.current_time()
    process_manger.kill_old_process(sys.argv[0])
    import logging
    config = {"job_name": "secoo_month_job"
              , "spider_num": 40
              , "retries": 3
              , "request_timeout": 10
              , "complete_timeout": 1*60
              , "sleep_interval": 10
              , "rest_time": 15
              , "write_seed" : True
              , "mongo_config": {"addr": "mongodb://192.168.0.13:27017", "db": "secoo", "collection": "secoComment" + current_date}
              , "log_config": {"level": logging.ERROR, "filename": sys.argv[0] + '.logging', "filemode":'a',"format":'%(asctime)s - %(filename)s - %(processName)s - [line:%(lineno)d] - %(levelname)s: %(message)s'}
              }
    p = SecooMonthJob(current_date, **config)
    p.main_loop(show_process=True)
