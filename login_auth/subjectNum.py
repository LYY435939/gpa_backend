import re
import threading
import requests
from bs4 import BeautifulSoup
import http.client
import json
from codecs import encode

import func_timeout
from fake_headers import Headers
from func_timeout import func_set_timeout
from requests import Session
from concurrent.futures import ThreadPoolExecutor
import pymysql


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
        rtn = json.loads(res)['data']
        if rtn["need"]:
            print("need")
            const = {
                "username": "",  # your username
                "password": ""  # your password
            }
            res = requests.post(detect_url, headers=self.header, data=const)
            rtn = json.loads(res.content.decode("utf-8"))['data']
        self.mfa = rtn["state"]
        print(self.mfa, rtn["need"])
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
        print("login prepare")
        if re.search("欢迎", res.content.decode("utf-8")) is None:
            return None

        self.session.get(
            "https://uis.nwpu.edu.cn/cas/login?service=https%3A%2F%2Fjwxt.nwpu.edu.cn%2Fstudent%2Fsso-login",
            headers=self.header)
        return self.session


if __name__ == '__main__':
    username = ""  # your username
    password = ""  # your password
    req = Req({
        "username": username,
        "password": password
    })
    req.login()
    print("login")
    r = req.session.get(
        url='https://jwxt.nwpu.edu.cn/student/ws/major-select/data/mulMajors?bizTypeId=2&ignoreOpenInfoEnableStatus=false&ignoreDepartmentChildren=true')
    r = json.loads(r.content.decode("utf-8"))
    ids = []
    for id in r:
        ids.append(id["id"])
    print("write")
    db = pymysql.connect(
        host='',
        user='gpa',
        password='',
        database='gpa')


    def setNum(grade, id):
        print(grade, id)
        r = req.session.get(
            url=f'https://jwxt.nwpu.edu.cn/student/for-std/student-portrait/getGradeAnalysis?bizTypeAssoc=2&grade={grade}&majorAssoc={id}&semesterAssoc=')
        # print(r.content.decode("utf-8"))
        r = json.loads(r.content.decode("utf-8"))['scoreRangeCount']
        A = r['[90, 100]']
        B = r['[80, 90)']
        C = r['[70, 80)']
        D = r['[60, 70)']
        E = r['[0, 60)']
        sum = A + B + C + D + E
        print(A, B, C, D, E, sum)
        cur.execute(f'''
            insert into subject_number(subject, A, B, C, D, E, SUM, GRADE) VALUES (
            {id},{A},{B},{C},{D},{E},{sum},{grade}
            )
        ''')
        # cur.execute(f'''
        #     update subject_number set
        #     A={A},B={B},C={C},D={D},E={E},sum={sum}
        #     where `subject`={id} and `grade`={grade}
        # ''')
        print(grade, id, 'OK')


    threadPool = ThreadPoolExecutor(max_workers=50)
    with db.cursor() as cur:
        grades = [2018, 2019, 2020, 2021, 2022, 2023]
        for grade in grades:
            for id in ids:
                threadPool.submit(setNum(grade, id))
    threadPool.shutdown()
    db.commit()
