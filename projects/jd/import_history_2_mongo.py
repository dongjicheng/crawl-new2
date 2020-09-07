#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mongo import op
import os
import glob
from multiprocess.tools import timeUtil
os.chdir("/home/u9000/martingale/jd_month/")
current_date = timeUtil.current_time()
with op.DBManger() as db:
    db.load_file_to_db(filename="month202006", db_collect=("jingdong", "month202006"),sep="\t",buffer_size=128,
                       column_index_list=[0,14,28,29,30,31], fields_tupe=("skuid","comment","price","cate_id","brand_id","ziying"), attach_dict={"_month": 202006})