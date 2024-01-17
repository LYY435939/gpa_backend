import asyncio
import json
import random
import re
import threading
from multiprocessing.dummy import Pool
from concurrent.futures import ThreadPoolExecutor

import aiohttp
import requests
from bs4 import BeautifulSoup
from login_auth.mfa import *
from login_auth.models import *
from django.db import connection


# import grequests


class Req:
    def __init__(self, user, cookies=None, gid=None, mfa=None):
        self.session = StableReq(requests.session())
        if cookies is not None:
            self.session.session.cookies = cookies
        self.username = user["username"]
        self.password = user["password"]
        self.mfa = mfa
        self.gid = gid
        self.cur = None
        self.studentId = None
        self.rank = None
        self.score = None
        self.need = True
        self.header = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 Edg/106.0.1370.37"
        }
        student = Student.objects.filter(username=self.username).first()
        if student is not None:
            self.studentId = student.studentId
        with connection.cursor() as cur:
            self.cur = cur

    def getMfa(self):
        detect_url = 'https://uis.nwpu.edu.cn/cas/mfa/detect'
        res = newMfa(self.username, self.password)
        rtn = json.loads(res)['data']
        self.mfa = rtn["state"]
        self.need = rtn["need"]
        return rtn["need"]

    def send(self):
        securephoneURL = "https://uis.nwpu.edu.cn/cas/mfa/initByType/securephone"
        res = json.loads(requests.get(securephoneURL, headers=self.header, params={"state": self.mfa})
                         .content.decode("utf-8"))['data']
        attestServerUrl = res["attestServerUrl"]
        self.gid = res["gid"]
        securePhone = res["securePhone"]
        sendURL = attestServerUrl + "/api/guard/securephone/send"
        res = json.loads(requests.post(sendURL, headers=self.header, json={"gid": self.gid})
                         .content.decode("utf-8"))['data']
        print(res)
        return {
            "gid": self.gid,
            "securePhone": securePhone
        }

    def login(self):
        login = "https://uis.nwpu.edu.cn/cas/login"
        res = self.session.get(login, headers=self.header)
        html = BeautifulSoup(res.content.decode("utf-8"), 'lxml')
        fm1 = html.find(id='fm1')
        execution = fm1.find_all("input")[4]["value"]

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
            return False
        self.session.get(
            "https://uis.nwpu.edu.cn/cas/login?service=https%3A%2F%2Fjwxt.nwpu.edu.cn%2Fstudent%2Fsso-login",
            headers=self.header)
        return self.session

    def getStuId(self):
        if self.studentId is not None:
            print("Get StudentId OK")
            return self.studentId
        print("Get StudentId Start")
        try_times = 0
        while True:
            try:
                res = self.session.get("https://jwxt.nwpu.edu.cn/student/for-std/student-info",
                                       allow_redirects=False)
                res_code = res.status_code
                if res_code == 302:
                    search = re.search(r"[0-9]+", res.headers["Location"])
                    if search is not None:
                        self.studentId = search.group(0)
                    else:
                        raise Exception("ERROR")
                else:
                    html = BeautifulSoup(res.content.decode("utf-8"), 'lxml')
                    self.studentId = html.find_all("button")[0]["value"]
                print(self.studentId)
                break
            except Exception or IndexError:
                if try_times > 5:
                    raise Exception("Too many tries while getting studentId")
                try_times = try_times + 1
        student = Student.objects.filter(username=self.username).first()
        if student is None:
            Student(username=self.username, studentId=self.studentId).save()
        else:
            if self.cur is not None:
                self.cur.execute(f'''
            update student 
            set password='{self.password}', studentId='{self.studentId}' 
            where username='{self.username}'
            ''')
        connection.commit()
        print("Get StudentId OK")
        return self.studentId

    def getRank(self):
        self.getStuId()
        print("GET rank Start")
        res = self.session.get(
            f"https://jwxt.nwpu.edu.cn/student/for-std/student-portrait/getMyGrades?studentAssoc={self.studentId}&semesterAssoc=")
        score = json.loads(res.content.decode("utf-8"))
        rank = score["stdGpaRankDto"]
        rank["avgMajorGpa"] = score['avgMajorGpa']
        res = self.session.get(
            'https://jwxt.nwpu.edu.cn/student/for-std/student-portrait/getStdInfo?bizTypeAssoc=2&cultivateTypeAssoc=1'
        )
        r = json.loads(res.content.decode("utf-8"))
        grade = r['recruitInfo']['student']['enterSchoolGrade']
        major = r['recruitInfo']['student']['major']['id']
        sn = SubjectNumber.objects.filter(subject=major, grade=grade).first()
        rank['num'] = [sn.A, sn.B, sn.C, sn.D, sn.E, sn.sum]
        print("GET rank OK")
        self.rank = rank
        return rank

    def getScore(self):
        self.getStuId()
        url = f"https://jwxt.nwpu.edu.cn/student/for-std/grade/sheet/info/{self.studentId}"
        res = self.session.get(url).json()
        print("GET score OK")
        return res

    # def GScore(self):
    #     print(self.session.session.headers)
    #
    #     self.getStuId()
    #     url = f"https://jwxt.nwpu.edu.cn/student/for-std/grade/sheet/semester-index/{self.studentId}"
    #     res = self.session.get(url).content.decode("utf-8")
    #     pattern = re.compile(r'JSON.parse\([\'](.*?)[\']', re.S)
    #     js = re.findall(pattern, res)[0].replace("\\", "")
    #     semesters = json.loads(js)
    #
    #     Semesters = []
    #     id_list = []
    #
    #     print("GET score Start")
    #
    #     for s in semesters:
    #         id = s["id"]
    #         threading.Thread(target=(lambda id: Semesters.append({
    #             "courses": [],
    #             "id": id,
    #             "name": ""
    #         })), args=(id,)).start()
    #         threading.Thread(target=(lambda id: id_list.append(id)), args=(id,)).start()
    #
    #     rs = (grequests.get(
    #         headers=self.session.session.headers,
    #         url=f"https://jwxt.nwpu.edu.cn/student/for-std/grade/sheet/info/{self.studentId}?semester={id}"
    #     ) for id in id_list)
    #     rs = grequests.map(rs)
    #     for r in rs:
    #         courses = json.loads(r.content.decode("utf-8"))["semesterId2studentGrades"][f"{id}"]
    #         allCourses = []
    #         thread_pool = ThreadPoolExecutor(max_workers=10)
    #         for course in courses:
    #             thread_pool.submit(lambda course: allCourses.append({
    #                 "name": course["course"]["nameZh"],
    #                 "grade": course["gaGrade"],
    #                 "gpa": course["gp"],
    #                 "credits": course["course"]["credits"]
    #             }), course)
    #         i = id_list.index(id)
    #         Semesters[i]["courses"] = allCourses
    #         Semesters[i]["name"] = courses[0]["semester"]["nameZh"]
    #
    #     print("GET score OK")
    #     self.score = Semesters
    #     return Semesters

    def AsyncScore(self):
        async def query(id):
            async with aiohttp.ClientSession() as s:
                async with s.get(
                        headers=self.session.session.headers,
                        cookies=self.session.session.cookies,
                        url=f"https://jwxt.nwpu.edu.cn/student/for-std/grade/sheet/info/{self.studentId}?semester={id}"
                ) as r:
                    jr = (await r.read()).decode("utf-8")
                    courses = json.loads(jr)["semesterId2studentGrades"][f"{id}"]
                    allCourses = []
                    thread_pool = ThreadPoolExecutor(max_workers=10)
                    for course in courses:
                        thread_pool.submit(lambda course: allCourses.append({
                            "name": course["course"]["nameZh"],
                            "grade": course["gaGrade"],
                            "gpa": course["gp"],
                            "credits": course["course"]["credits"]
                        }), course)
                    i = id_list.index(id)
                    Semesters[i]["courses"] = allCourses
                    Semesters[i]["name"] = courses[0]["semester"]["nameZh"]
                    await s.close()

        print("GET score Start")
        self.getStuId()
        url = f"https://jwxt.nwpu.edu.cn/student/for-std/grade/sheet/semester-index/{self.studentId}"
        res = self.session.get(url)
        if res.status_code != 200:
            raise Exception("503 Service Temporarily Unavailable")
        res = res.content.decode("utf-8")
        pattern = re.compile(r'JSON.parse\([\'](.*?)[\']', re.S)
        js = re.findall(pattern, res)[0].replace("\\", "")
        semesters = json.loads(js)

        Semesters = []
        id_list = []

        loop = asyncio.get_event_loop()

        for s in semesters:
            id = s["id"]
            threading.Thread(target=(lambda id: Semesters.append({
                "courses": [],
                "id": id,
                "name": ""
            })), args=(id,)).start()
            threading.Thread(target=(lambda id: id_list.append(id)), args=(id,)).start()

        tasks = []

        for i in id_list:
            tasks.append(asyncio.ensure_future(query(i)))

        loop.run_until_complete(asyncio.wait(tasks))

        print("GET score OK")
        self.score = Semesters
        return Semesters

    def fastScore(self):
        print("GET score Start")
        self.getStuId()
        url = f"https://jwxt.nwpu.edu.cn/student/for-std/grade/sheet/semester-index/{self.studentId}"
        res = self.session.get(url).content.decode("utf-8")
        pattern = re.compile(r'JSON.parse\([\'](.*?)[\']', re.S)
        js = re.findall(pattern, res)[0].replace("\\", "")
        semesters = json.loads(js)

        Semesters = []
        id_list = []

        def query(id):
            r = self.session.get(
                f"https://jwxt.nwpu.edu.cn/student/for-std/grade/sheet/info/{self.studentId}?semester={id}")
            courses = json.loads(r.content.decode("utf-8"))["semesterId2studentGrades"][f"{id}"]
            allCourses = []
            thread_pool = ThreadPoolExecutor(max_workers=10)
            for course in courses:
                thread_pool.submit(lambda course: allCourses.append({
                    "name": course["course"]["nameZh"],
                    "grade": course["gaGrade"],
                    "gpa": course["gp"],
                    "credits": course["course"]["credits"]
                }), course)
            i = id_list.index(id)
            Semesters[i]["courses"] = allCourses
            Semesters[i]["name"] = courses[0]["semester"]["nameZh"]

        ls = int(len(semesters) / 1)
        ls = 1 if ls == 0 else ls
        pool = Pool(ls)
        for s in semesters:
            id = s["id"]
            threading.Thread(target=(lambda id: Semesters.append({
                "courses": [],
                "id": id,
                "name": ""
            })), args=(id,)).start()
            threading.Thread(target=(lambda id: id_list.append(id)), args=(id,)).start()
        pool.map(query, id_list)
        pool.close()
        pool.join()
        print("GET score OK")
        self.score = Semesters
        return Semesters
