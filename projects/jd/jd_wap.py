#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import sys

from multiprocess.core.spider import SpiderManger, Seed
from multiprocess.tools import process_manger
from multiprocess.tools import timeUtil, collections
import random
import time
from fake_useragent import UserAgent

from multiprocess.core import HttpProxy


class GetComment(SpiderManger):
    def __init__(self, seeds_file, dateindex, **kwargs):
        super(GetComment, self).__init__(**kwargs)
        self.ua = UserAgent()
        with open(seeds_file) as infile:
            data_set = collections.DataSet(infile)
            for i, seed in enumerate(data_set.map(lambda line: line.strip('\n').split("\t")[0])
                                             .shuffle(2048)):
                self.seeds_queue.put(Seed(seed, kwargs["retries"]))
        self.allcnt_pattern = re.compile(r'"commentCount":(\d+),')
        self.dateindex = dateindex

    def make_request(self, seed):
        url = "https://club.jd.com/comment/skuProductPageComments.action?callback=fetchJSON_comment98&productId={0}&score=0&sortType=5&page=0&pageSize=10&isShadowSku=0&fold=1".format(seed.value)
        request={"url": url,
         "method":"get",
         "allow_redirects":False,
         "sleep_time": 0.156 + random.random() / 10,
         "proxies":{"https": self.current_proxy, "http":self.current_proxy},
         "headers":{
         'Host': 'club.jd.com',
         'Connection': 'keep-alive',
         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36',
         'Referer': 'https://item.jd.com/{0}.html'.format(seed.value)
        }}
        return request

    def parse_item(self, content, seed):
        result = []
        count = self.allcnt_pattern.findall(content)
        if not count:
            result.append({"skuid": seed.value, "comment": "0", "_seed":seed.value})
        else:
            result.append({"skuid": seed.value, "comment": str(count[0]),"_seed":seed.value})
        #r = (0.1563 + random.random() / 10)
        #time.sleep(r)
        if result:
            self.write(result)
            seed.ok()


if __name__ == "__main__":
    current_date = timeUtil.current_time()
    process_manger.kill_old_process(sys.argv[0])
    import logging
    new_config = {"job_name": "jdcomment"
              , "spider_num": 1
              , "retries": 3
              ,"rest_time":5
              , "complete_timeout": 1*60
              , "seeds_file": "resource/month202007"
              , "dateindex": current_date
              , "mongo_config": {"addr": "mongodb://192.168.0.13:27017", "db": "jicheng",
                                 "collection": "comment" + current_date}
              , "log_config": {"level": logging.DEBUG, "filename": sys.argv[0] + '.logging', "filemode":'a', "format":'%(asctime)s - %(filename)s - %(processName)s - [line:%(lineno)d] - %(levelname)s: %(message)s'}
              , "proxies_pool": HttpProxy.getHttpsProxy()
                  }
    p = GetComment(**new_config)
    p.main_loop(show_process=True)
