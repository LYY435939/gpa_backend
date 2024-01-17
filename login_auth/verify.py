import json
import re

import requests
from bs4 import BeautifulSoup
import json
import random
import re
import threading
from multiprocessing.dummy import Pool
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup
import http.client
import json
from codecs import encode

import func_timeout
from fake_headers import Headers
from func_timeout import func_set_timeout
from requests import Session


@func_set_timeout(1)
def getMfa(username: str, password: str):
    conn = http.client.HTTPSConnection("uis.nwpu.edu.cn")
    dataList = []
    boundary = 'wL36Yn8afVp8Ag7AmP8qZ0SA4n1v9T'
    dataList.append(encode('--' + boundary))
    dataList.append(encode('Content-Disposition: form-data; name=username;'))

    dataList.append(encode('Content-Type: {}'.format('text/plain')))
    dataList.append(encode(''))

    dataList.append(encode(f"{username}"))
    dataList.append(encode('--' + boundary))
    dataList.append(encode('Content-Disposition: form-data; name=password;'))

    dataList.append(encode('Content-Type: {}'.format('text/plain')))
    dataList.append(encode(''))

    dataList.append(encode(f"{password}"))
    dataList.append(encode('--' + boundary + '--'))
    dataList.append(encode(''))
    body = b'\r\n'.join(dataList)
    payload = body
    header = Headers(
        browser="chrome",  # Generate only Chrome UA
        os="win",  # Generate ony Windows platform
        headers=True  # generate misc headers
    ).generate()
    headers = {
        'User-Agent': header['User-Agent'], 'Accept': '*/*', 'Host': 'uis.nwpu.edu.cn',
        'Connection': 'keep-alive',
        'Content-Type': 'multipart/form-data; boundary=--------------------------801807044462781399830225',
        'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
    }
    conn.request("POST", "/cas/mfa/detect", payload, headers)
    res = conn.getresponse()
    data = res.read()
    return json.loads(data)


def newMfa(username, password):
    while True:
        try:
            d = getMfa(username, password)
            break
        except func_timeout.exceptions.FunctionTimedOut:
            pass
    return json.dumps(d)


class StableReq:
    def __init__(self, session: Session):
        self.session = session

    @func_set_timeout(4)
    def rawGet(self, url, **kwargs):
        return self.session.get(url, **kwargs)

    @func_set_timeout(4)
    def rawPost(self, url, **kwargs):
        return self.session.post(url, **kwargs)

    def get(self, url, **kwargs):
        while True:
            try:
                r = self.rawGet(url, **kwargs)
                break
            except func_timeout.exceptions.FunctionTimedOut:
                pass
        return r

    def post(self, url, **kwargs):
        while True:
            try:
                r = self.rawPost(url, **kwargs)
                break
            except func_timeout.exceptions.FunctionTimedOut:
                pass
        return r


class Req:
    def __init__(self, user):
        self.session = StableReq(requests.session())
        self.username = user["username"]
        self.password = user["password"]
        self.mfa = None
        self.studentId = None
        self.header = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 Edg/106.0.1370.37"
        }

    def getMfa(self):

        detect_url = 'https://uis.nwpu.edu.cn/cas/mfa/detect'
        user = {
            "username": self.username,
            "password": self.password
        }
        res = newMfa(self.username, self.password)
        print(res)
        rtn = json.loads(res)['data']
        if rtn["need"]:
            print("need")
            const = {
                "username": "",
                "password": ""
            }
            res = requests.post(detect_url, headers=self.header, data=const)
            rtn = json.loads(res.content.decode("utf-8"))['data']
        self.mfa = rtn["state"]
        return rtn["need"]

    # return self.mfa

    def login(self):

        t1 = threading.Thread(target=self.getMfa(), args=())
        t1.start()
        # self.getMfa()
        login = "https://uis.nwpu.edu.cn/cas/login"
        res = self.session.get(login, headers=self.header)
        html = BeautifulSoup(res.content.decode("utf-8"), 'lxml')
        # result = html.xpath(" //input[@name='execution']")
        fm1 = html.find(id='fm1')
        execution = fm1.find_all("input")[4]["value"]
        t1.join()
        data = {
            "username": self.username,
            "password": self.password,
            "mfaState": self.mfa,
            "_eventId": "submit",
            "execution": execution,
            "geolocation": "",
            "submit": "稍等片刻……"
        }
        res = self.session.post(login, headers=self.header, data=data)
        if re.search("欢迎", res.content.decode("utf-8")) is None:
            return None
        # print(res.text)
        # self.session.get("https://ecampus.nwpu.edu.cn/main.html#/Index", headers=header)
        self.session.get("https://jwxt.nwpu.edu.cn/student/sso-login", headers=self.header)

        return self.session

    def getStuId(self):
        if self.studentId is not None:
            return self.studentId
        res = self.session.get("https://jwxt.nwpu.edu.cn/student/for-std/student-info")
        search = re.search(r"[0-9]+", res.url)
        if search is None:
            html = BeautifulSoup(res.content.decode("utf-8"), 'lxml')
            self.studentId = html.find_all("button")[0]["value"]
        else:
            self.studentId = search.group(0)
        print(self.studentId)
        # self.studentId = re.search(r"[0-9]+", res.url).group(0)
        return self.studentId


if __name__ == '__main__':
    username = ""               # your username
    password = ""               # your password
    req = Req({
        "username": username,
        "password": password
    })
    need = req.getMfa()
    if need:
        r = requests.get("https://uis.nwpu.edu.cn/cas/mfa/initByType/securephone", params={
            "state": req.mfa
        }, headers=req.header).content.decode("utf-8")
        r = json.loads(r)
        gid = r["data"]["gid"]
        print(gid)
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36'
        }
        data = f'{{"gid":"{gid}"}}'
        print(data)
        r = requests.post("https://uis.nwpu.edu.cn/attest/api/guard/securephone/send",
                          data=data, headers=headers) \
            .content.decode("utf-8")
        print(r)
        code = input("input code:")
        print(code)
        data = f'{{"gid":"{gid}","code":"{code}"}}'
        print(data)
        r = requests.post("https://uis.nwpu.edu.cn/attest/api/guard/securephone/valid",
                          data=data, headers=headers) \
            .content.decode("utf-8")
        print(r)
        login = "https://uis.nwpu.edu.cn/cas/login"
        res = req.session.get(login, headers=req.header)
        html = BeautifulSoup(res.content.decode("utf-8"), 'lxml')
        # result = html.xpath(" //input[@name='execution']")
        fm1 = html.find(id='fm1')
        execution = fm1.find_all("input")[4]["value"]
        data = {
            "username": username,
            "password": password,
            "mfaState": req.mfa,
            "_eventId": "submit",
            "execution": execution,
            "geolocation": "",
            "submit": "稍等片刻……"
        }
        res = req.session.post(login, headers=req.header, data=data)
        if re.search("欢迎", res.content.decode("utf-8")) is not None:
            print("verify ok")
        else:
            print("verify failed")
    else:
        print("no need")
