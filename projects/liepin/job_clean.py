#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mongo import op
from tqdm import tqdm
job_table = "job_20200617"
pipeline=[
    {
        "$lookup": {
            "from": "companyALL_2",
            "localField": "formdata.ecompIds",
            "foreignField": "_id",
            "as": "company"
        }
    },
    {
        "$unwind": "$data.list"
    },
    {
        "$project": {
            "_id": 0,
            "ecompIds": "$formdata.ecompIds",
            "name": {
                "$arrayElemAt": [
                    "$company.name",
                    0
                ]
            },
            "dq": {
                "$arrayElemAt": [
                    "$company.dq",
                    0
                ]
            },
            "industry": {
                "$arrayElemAt": [
                    "$company.industry",
                    0
                ]
            },
            "e_kind": {
                "$arrayElemAt": [
                    "$company.e_kind",
                    0
                ]
            },
            "salary": "$data.list.salary",
            "city": "$data.list.city",
            "title": "$data.list.title",
            "refreshTime": "$data.list.refreshTime",
            "ejobId": "$data.list.ejobId",
            "dept": "$data.list.dept",
            "hot": "$data.list.hot",
            "citySEOUrl": "$data.list.citySEOUrl",
            "time": "$data.list.time",
            "workYear": "$data.list.workYear",
            "feedbackPeriod": "$data.list.feedbackPeriod",
            "eduLevel": "$data.list.eduLevel"
        }
    },
    {
        "$group": {
            "_id": {
                "ecompIds": "$ecompIds",
                "ejobId": "$ejobId"
            },
            "name": {
                "$first": "$name"
            },
            "dq": {
                "$first": "$dq"
            },
            "industry": {
                "$first": "$industry"
            },
            "e_kind": {
                "$first": "$e_kind"
            },
            "salary": {
                "$first": "$salary"
            },
            "city": {
                "$first": "$city"
            },
            "title": {
                "$first": "$title"
            },
            "refreshTime": {
                "$first": "$refreshTime"
            },
            "dept": {
                "$first": "$dept"
            },
            "hot": {
                "$first": "$hot"
            },
            "citySEOUrl": {
                "$first": "$citySEOUrl"
            },
            "time": {
                "$first": "$time"
            },
            "workYear": {
                "$first": "$workYear"
            },
            "feedbackPeriod": {
                "$first": "$feedbackPeriod"
            },
            "eduLevel": {
                "$first": "$eduLevel"
            }
        }
    },
    {
        "$out": "{}_clean".format(job_table)
    }
]

with op.DBManger() as m:
    m.aggregate(db_collect=("liepin",job_table), pipeline=pipeline)