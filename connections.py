'''
LibreBika: An Open-source Third-party Client of PicaComic.
Copyright © 2021 by Stanley Jian <jianstanley@outlook.com>

This file is a part of LibreBika.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License Version 2 as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

@license GPL-2.0 <http://spdx.org/licenses/GPL-2.0>
'''

BK_DOMAIN='https://picaapi.picacomic.com/'
BK_VERSION='2.2.1.3.3.4'
BK_BUILD='45'
BK_KEY='C69BAF41DA5ABD1FFEDC6D2FEA56B'
BK_SIGNATURE='~d}$Q7$eIni=V)9\\RK/P.RM4;9[7|@/CA}b~OW!3?EV`:<>M7pddUBL5n|0/*Cn'
BK_ACCEPT='application/vnd.picacomic.com.v1+json'
BK_PLATFORM='android'
BK_UUID='defaultUuid'
BK_CONTENT_TYPE='application/json; charset=UTF-8'
BK_USER_AGENT='okhttp/3.8.1'
BK_CODES=['0','1','2','3','4','5','6','7','8','9','a','b','c','d','e','f']

import hmac,hashlib
import uuid
import json
import requests
import shutil
from time import time_ns

def bk_encryption(string):
    instance=hmac.new(BK_SIGNATURE.encode('utf-8'),string.lower().encode('utf-8'),hashlib.sha256)
    return ''.join([BK_CODES[(each&255)>>4]+BK_CODES[(each&255)&15] for each in instance.digest()])

def compile_params(params):
    if not type(params)==dict:
        return None
    return '?'+'&'.join([f'{str(each)}={str(params[each])}' for each in params])

def submit(path,channel,quality,is_post=True,params=None,payload={},token=None):
    if not is_post and payload!={}:
        return None
    time_sec=str(int(time_ns()/1000000000))
    uuid_str=uuid.uuid4().hex
    headers={
        'api-key':BK_KEY,
        'accept':BK_ACCEPT,
        'app-channel':channel,
        'time':time_sec,
        'nonce':uuid_str,
        'signature':bk_encryption(path+(compile_params(params) if params!=None else '')+time_sec+uuid_str+('POST' if is_post else 'GET')+BK_KEY),
        'app-version':BK_VERSION,
        'app-uuid':BK_UUID,
        'image-quality':quality,
        'app-platform':BK_PLATFORM,
        'app-build-version':BK_BUILD,
        'content-type':BK_CONTENT_TYPE,
        'user-agent':BK_USER_AGENT
    }
    if token!=None:
        headers['authorization']=token
    if is_post:
        if params==None:
            return requests.post(BK_DOMAIN+path,headers=headers,json=payload).text
        else:
            return requests.post(BK_DOMAIN+path,headers=headers,params=params,json=payload).text
    else:
        return requests.get(BK_DOMAIN+path,headers=headers,params=params).text

def log_in(username,password):
    resp=json.loads(submit('auth/sign-in','1','l',payload={'email':username,'password':password}))
    if resp['code']==200:
        return resp['data']['token']
    else:
        if resp['code']==400 and resp['error']=='1004':
            return '!用户凭证错误。代码：'+resp['error']
        else:
            return '!出现了未知的错误。代码：'+resp['error']

def validate_token(token):
    try:
        resp=json.loads(submit('init','1','l',is_post=False,params={'platform':'android'},token=token))
    except:
        return None
    if resp['code']!=200:
        return False
    return True

#Service methods below. Supply contextual data: token, channel, quality as a list
#None for no category constraint. page>0

def sv_keyword(context,keyword,sort,page,categories):
    payload={'keyword':keyword,'sort':sort}
    if categories!=None:
        payload['categories']=categories
    try:
        resp=json.loads(submit('comics/advanced-search',context[1],context[2],params={'page':str(page)},payload=payload,token=context[0]))
    except:
        return None
    if resp['code']!=200 and 'message' in resp:
        return int(resp['error'])
    return resp['data']['comics']

def sv_comic_episode(context,id,page):
    try:
        resp=json.loads(submit('comics/'+id+'/eps',context[1],context[2],is_post=False,params={'page':str(page)},token=context[0]))
    except:
        return None
    if resp['code']!=200 and 'message' in resp:
        return int(resp['error'])
    return resp['data']['eps']

def sv_comic_profile(context,id):
    try:
        resp=json.loads(submit('comics/'+id,context[1],context[2],is_post=False,token=context[0]))
    except:
        return None
    if resp['code']!=200 and 'message' in resp:
        return int(resp['error'])
    return resp['data']['comic']

def downloader(url,name):
    try:
        resp=requests.get(url,stream=True)
        if resp.status_code!=200:
            return False
        else:
            with open(name,'wb') as f:
                shutil.copyfileobj(resp.raw,f)
            return True
    except:
        return None

def sv_stamp(context):
    try:
        resp=json.loads(submit('users/punch-in',context[1],context[2],token=context[0]))
    except:
        return None
    if resp['code']!=200 and 'message' in resp:
        return int(resp['error'])
    return resp['data']['res']['status']=='ok'

def sv_user_profile(context):
    try:
        resp=json.loads(submit('users/profile',context[1],context[2],is_post=False,token=context[0]))
    except:
        return None
    if resp['code']!=200 and 'message' in resp:
        return int(resp['error'])
    return resp['data']['user']

def sv_comic_resource_list(context,id,idx,page):
    try:
        resp=json.loads(submit('comics/'+id+'/order/'+str(idx)+'/pages',context[1],context[2],is_post=False,params={'page':str(page)},token=context[0]))
    except:
        return None
    if resp['code']!=200 and 'message' in resp:
        return int(resp['error'])
    return resp['data']['pages']
