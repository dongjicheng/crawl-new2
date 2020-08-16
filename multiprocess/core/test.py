#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pycurl
import chardet
from  io import BytesIO
import re
def download(request):
    request_url = request.get("url")
    headers = request.get("headers")
    if isinstance(headers, dict):
        headers = [k + ":" + v for k, v in headers.items()]
    proxies = request.get("proxies")
    mothed = request.get("mothed")

    c = pycurl.Curl()
    body = BytesIO()
    c.setopt(pycurl.VERBOSE, True)
    c.setopt(pycurl.HEADER, False)
    c.setopt(pycurl.TIMEOUT, 3)
    c.setopt(pycurl.CONNECTTIMEOUT, 1)
    c.setopt(pycurl.URL, request_url)
    if headers:
        print(headers)
        c.setopt(pycurl.HTTPHEADER, headers)
    c.setopt(pycurl.ENCODING, 'gzip,deflate')
    c.setopt(pycurl.SSL_VERIFYPEER, False)
    c.setopt(pycurl.SSL_VERIFYHOST, False)
    if mothed is None:
        mothed = "get"
    if mothed.lower() == "post":
        c.setopt(pycurl.POST, 1)
        data = request.get("data")
        if data:
            c.setopt(pycurl.POSTFIELDS, data)
    c.setopt(pycurl.WRITEFUNCTION, body.write)
    if proxies:
        proxy, password = convert_proxy_format(proxies)
        c.setopt(pycurl.PROXY, proxy)
        c.setopt(pycurl.PROXYUSERPWD, password)
    try:
        c.perform()
        code = c.getinfo(pycurl.RESPONSE_CODE)
        content = c.getinfo(pycurl.CONTENT_TYPE)
        if code != 200:
            raise pycurl.error(code, "")
    except pycurl.error as err:
        print(repr(err))
        raise err
    finally:
        c.close()
    return body.getvalue().decode("gbk")

def convert_proxy_format(proxy="http://u0:crawl@192.168.0.71:3128"):
    password = proxy[proxy.find("//") + 2: proxy.find("@")]
    proxy = proxy.replace(password + "@", "")
    return proxy, password
import requests
from multiprocess.core.HttpProxy import getHttpProxy
for proxy in getHttpProxy():
    request = {"url": "https://www.baidu.com/s?wd=ip",
                       "proxies": {"http":proxy},
                       "headers":{
             'Connection': 'close',
             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36',
            }}


    first_pettern = re.compile(r'<span class="c-gap-right">本机IP:&nbsp;(.*?)</span>',re.MULTILINE)
    print((proxy,first_pettern.findall(requests.get(**request))))