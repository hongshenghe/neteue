#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2011 ~ 2013 Deepin, Inc.
#               2011 ~ 2013 Hou ShaoHui
# 
# Author:     Hou ShaoHui <houshao55@gmail.com>
# Maintainer: Hou ShaoHui <houshao55@gmail.com>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time
import logging
import os
import re
import cookielib
import json
import pycurl
import urllib


from utils import Curl, parser_json
import utils

loglevel = logging.DEBUG
console_format = "%(levelname)-8s: %(message)s"
datefmt = "%H:%M:%S"
logging.basicConfig(level=loglevel, format=console_format, datefmt=datefmt)
logger = logging.getLogger(__name__)

def format_size(num, unit='B'):
    next_unit_map = dict(B="K", K="M", M="G", G="T")
    if num > 1024:
        return format_size(num/1024, next_unit_map[unit])
    if num == 0:
        return "0%s  " % unit   # padding
    if unit == 'B':
        return "%.0f%s" % (num, unit)
    return "%.1f%s" % (num, unit)


TASK_STATUS = {0: u'\u4e0b\u8f7d\u6210\u529f',
               1: u'\u4e0b\u8f7d\u8fdb\u884c\u4e2d',
               2: u'\u7cfb\u7edf\u9519\u8bef',
               3: u'\u8d44\u6e90\u4e0d\u5b58\u5728',
               4: u'\u4e0b\u8f7d\u8d85\u65f6',
               5: u'\u8d44\u6e90\u5b58\u5728\u4f46\u4e0b\u8f7d\u5931\u8d25',
               6: u'\u5b58\u50a8\u7a7a\u95f4\u4e0d\u8db3',
               7: u'\u4efb\u52a1\u53d6\u6d88',
               8: u'\u76ee\u6807\u5730\u5740\u6570\u636e\u5df2\u5b58\u5728',
               9: u'\u4efb\u52a1\u5220\u9664'}



class NetPan(object):
    
    def __init__(self, username, password):
        self.cookie_file = utils.get_cookie_file(username)
        self.curl = Curl(self.cookie_file)
        self.username = username
        self.password = password
        self.__bduss = None
    
    def check_login(self, stage=0):
        self.curl.request("http:/pan.baidu.com/")
        ret = self.api_request("https://pan.baidu.com/api/account/thirdinfo")
        if ret["errno"] == 0:
            logger.debug("Login check success!")
            return True
        
        # 登陆校验失败(超过两次登陆校验)
        if stage >= 2:
            logger.debug("Login check failed!")
            return False
        
        login_url = 'https://passport.baidu.com/v2/api/?login&tpl=mn&time=%d' % utils.timestamp()
        data = self.curl.request(login_url).strip()[1:-1]
        
        data = eval(data, type('Dummy', (dict,), dict(__getitem__=lambda s,n:n))())
        if int(data["error_no"]) != 0:
            logger.debug("Login passport error")
            return False
        
        param_out = data["param_out"]
        param_in = data["param_in"]
        params = {v : param_out[k.replace("name", "contex")] for k, v in param_out.items() if k.endswith("_name")}
        params.update({v: param_in[k.replace("name", "value")] for k,v in param_in.items() if k.endswith("_name")})
        params["username"] = self.username.decode("utf-8").encode("gbk")
        params["password"] = self.password
        params["safeflg"]  = ""
        params["mem_pass"] = "on"
        if params["verifycode"] and stage == 1:
            self.loginfo("Login check require verifycode")
            
        params['staticpage'] = "http://pan.baidu.com/res/static/thirdparty/pass_v3_jump.html"
            
        html = self.curl.request("https://passport.baidu.com/v2/api/?login", 
                                 data=params, method="POST")        
        
        url = re.findall(r"encodeURI\('(.*?)'\)", html)[0]
        self.curl.request(url)
        return self.check_login(stage + 1)
    
    def api_request(self, url, method="GET", extra_data=dict(), retry_limit=2, encoding=None, **params):
        ret = None
        data = {}
        data.update(extra_data)
        data.update(params)
        for key in data:
            if callable(data[key]):
                data[key] = data[key]()
            if isinstance(data[key], (list, tuple, set)):
                data[key] = ",".join(map(str, list(data[key])))
            if isinstance(data[key], unicode):    
                data[key] = data[key].encode("utf-8")
                
        start = time.time()        
        ret = self.curl.request(url, data, method)
        if ret == None:
            if retry_limit == 0:
                logger.debug("API request error: url=%s" % self.curl.url)
                return dict()
            else:
                retry_limit -= 1
                return self.api_request(url, method, extra_data, retry_limit, **params)
            
        if encoding != None:    
            ret = ret.decode(encoding)
        data = parser_json(ret)       
        logger.debug("API response %s: TT=%.3fs", self.curl.url,  time.time() - start )
        return data
    
    def _bduss(self):
        if self.__bduss != None:
            return self.__bduss
        
        cj = cookielib.MozillaCookieJar(self.cookie_file)
        cj.load()
        for c in cj:
            if c.name == 'BDUSS' and c.domain.endswith('.baidu.com'):
                self.__bduss = c.value
                return c.value
        raise RuntimeError('BDUSS cookie not found')

    
    def _wget_analytics(self, method='http'):
        params = dict(_lsid = utils.timestamp(),
                      _lsix = 1,
                      page = 1,
                      clienttype = 0,
                      type = "offlinedownloadtaskmethod",
                      method = method)
        ret =  self.api_request("http://pan.baidu.com/api/analytics", extra_data=params)
        if ret['errno'] != 0:
            raise RuntimeError("method not supported")
        
    def wget(self, url, save_to="/"):    
        self._wget_analytics()
        params = dict(method = "add_task",
                      app_id = 250528,
                      BDUSS = self._bduss(),
                      source_url = url,
                      save_path = save_to)
        ret = self.api_request("http://pan.baidu.com/rest/2.0/services/cloud_dl",
                               method="POST", extra_data=params)
        return ret['task_id']
    
    def status(self, task_id):
        taskids = ','.join(task_id) if isinstance(task_id, (list, tuple)) else str(task_id)
        params = dict(method = 'query_task',
                      app_id = 250528,
                      BDUSS = self._bduss(),
                      task_ids = taskids,
                      op_type = 1,
                      t = utils.timestamp())
        ret = self.api_request("http://pan.baidu.com/rest/2.0/services/cloud_dl",
                               method="POST", extra_data=params)
        for tid, task in ret['task_info'].items():
            if task.get('finish_time', 0):
                desc = u"完成于 " + time.ctime(int(task['finish_time']))
            else:
                try:
                    desc = u"%3.2f%%" % (int(task['finished_size']) / int(task['file_size']) * 100)
                except:
                    desc = u'未知状态'
            print tid, TASK_STATUS[int(task['status'])], desc
        return ret['task_info']
    
    def watch(self, task_id):
        while True:
            tasks = self.status(task_id)
            #print tasks
            if any(map(lambda t: int(t['status']) == 1, tasks.values())):
                time.sleep(6)
                continue
            break
        return
    
    def list_task(self):
        params = dict(method='list_task',
                     app_id=250528,
                     BDUSS=self._bduss(),
                     need_task_info=1,
                     status=255,
                     t=utils.timestamp())
        ret = self.api_request("http://pan.baidu.com/rest/2.0/services/cloud_dl",
                               method="POST", extra_data=params)
        return ret["task_info"]
    
    def _list(self, dir="/", page=1, initialCall=True):
        # None for error
        params = dict(channel='chunlei',
                      clienttype=0,
                      web=1,
                      num=100,
                      t=utils.timestamp(),
                      page=page,
                      dir=dir,
                      _=utils.timestamp())
        ret = self.api_request("http://pan.baidu.com/api/list", 
                               extra_data=params)
        files = ret['list']
        if len(files) == 100:
            files.extend(self._list(dir, page=page+1, initialCall=False))
        return files
    
    def list(self, dir="/"):
        files = self._list(dir)
        if files is None:
            print 'no such dir'
            return []
        print "total", len(files), dir
        for f in files:
            if f['isdir'] == 1:
                print 'd',
            else:
                print '-',
            print '\t', format_size(f.get('size', 0)),
            print '\t', time.strftime("%Y-%m-%d %H:%M",
                                      time.localtime(f['server_mtime'])),
            print '\t', f['server_filename']
        return files
    
    def isdir(self, dir):
        parent_path = os.path.dirname(dir)
        dir_name = unicode(os.path.basename(dir), 'utf-8')
        for d in self._list(parent_path):
            if dir_name == d['server_filename']:
                return True
        return False
    
    def remove(self, path):
        """remove file(s)"""
        paths = path if isinstance(path, (list, tuple)) else [path]
        params = dict(filelist=json.dumps(paths))
        
        ret = self.api_request("http://pan.baidu.com/api/filemanager?"
                               "channel=chunlei&clienttype=0&web=1&opera=delete",
                               method="POST", extra_data=params)
        if ret['errno'] == 0:
            for i in ret['info']:
                print i['path'], i['errno'] == 0
            return True
        else:
            print "error:", ret
            return False
        
    def rename(self, path, newname):
        newname = os.path.basename(newname)
        params = dict(filelist=json.dumps([dict(path=path,
                                                newname=newname)]))
        ret = self.api_request("http://pan.baidu.com/api/filemanager?"
                              "channel=chunlei&clienttype=0&web=1&opera=rename",
                               method="POST", extra_data=params)
        
        if ret['errno'] == 0:
            for i in ret['info']:
                print i['path'], i['errno'] == 0
        else:
            print "error:", ret

    def move(self, src, dst, newname):
        params = dict(filelist=json.dumps([dict(path=src,
                                                dest=dst,
                                                newname=newname or os.path.basename(src))]))
        ret = self.api_request("http://pan.baidu.com/api/filemanager?"
                               "channel=chunlei&clienttype=0&web=1&opera=move",
                               method="POST", extra_data=params)
        if ret['errno'] == 0:
            for i in ret['info']:
                print i['path'], i['errno'] == 0
        else:
            print "error:", ret

    def quota(self):
        params = dict(channel="chunlei",
                      clienttype=0,
                      web=1,
                      t=utils.timestamp())
        ret = self.api_request("http://pan.baidu.com/api/quota", extra_data=params)
        if ret['errno'] == 0:
            print format_size(ret['used']), "/", format_size(ret['total'])
            print "%3.2f%%" % (ret['used'] / ret['total'] * 100)
        else:
            print 'error', ret
            
    def _create(self, path, blocks, size, isdir=0):
        params = dict(path = path,
                      isdir = isdir,
                      size = size,
                      block_list = json.dumps(blocks),
                      method = 'post')
        ret = self.api_request("http://pan.baidu.com/api/create?a=commit&channel=chunlei&clienttype=0&web=1",
                               method="POST", extra_data=params)
        # {"fs_id":2157439985,"server_filename":"ck.txt","path":"\/ck.txt","size":1728,"ctime":1363701601,"mtime":1363701601,"isdir":0,"errno":0}
        if ret['errno'] == 0:
            print ret['path'], "save ok!"
        else:
            print 'error', ret
        return ret

    def upload(self, filepath, upload_to="/"):
        params = dict(method='upload',
                      type='tmpfile',
                      app_id=250528,
                      BDUSS=self._bduss())
        files = [("file", (pycurl.FORM_FILE, filepath)),]
        resp = self.curl.request("http://c.pcs.baidu.com/rest/2.0/pcs/file?" + \
                                   urllib.urlencode(params),
                                method="UPLOAD", data=files)
        ret = parser_json(resp)
        size = os.path.getsize(filepath)
        # {"md5":"16c1c8e61670eac54979f3da18b954ab","request_id":839611680}
        return self._create(os.path.join(upload_to, os.path.basename(filepath)),
                            [ret['md5']], size)

    def mkdir(self, path):
        return self._create(path, [], "", isdir=1)
