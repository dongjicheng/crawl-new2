#!/usr/bin/env python
# -*- coding: utf-8 -*-
from jingdong.spiders.jd_skuids2 import run_master
if __name__ == '__main__':
    run_master(retry=False, spider_num=1)

