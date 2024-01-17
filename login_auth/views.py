import asyncio
import json

from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import render
import base64
from Crypto.Cipher import PKCS1_v1_5
from Crypto import Random
from Crypto.PublicKey import RSA
from login_auth.models import *
from login_auth.reqMethods import *
import traceback


# Create your views here.
def setRSA(request):
    rsa = RSA.generate(2048)
    private_key = rsa.exportKey("PEM").decode("utf-8")
    public_key = rsa.publickey().exportKey().decode("utf-8")
    request.session['private_key'] = private_key
    return JsonResponseUtf8({
        "publicKey": public_key
    }, 200, False, "请重新下载安装")


def decodeData(request):
    private_key = request.session.get("private_key").encode("utf-8")
    raw_data = request.POST.get("data")
    data = decryption(raw_data, private_key)
    return json.loads(data)


def getScore(request):
    if request.method != 'POST':
        return JsonResponseUtf8({}, 405, False, "方法不允许")
    data = decodeData(request)
    username = data["username"]
    password = data["password"]

    forbidden = Forbidden.objects.filter(username=username).first()
    if forbidden is not None:
        return JsonResponseUtf8({}, 403, False, "禁止访问")
    else:
        if Forbidden.objects.filter(username='*').first():
            return JsonResponseUtf8({}, 403, False, "暂时不允许访问 Service Temporarily Unavailable")
    req = Req({
        "username": username,
        "password": password,
    })

    @func_set_timeout(20)
    def process():
        login = req.login()
        if login is None:
            return JsonResponseUtf8({}, 404, False, "账号或密码错误")
        print('login')
        LoginInfo(username=username, loginTime=timezone.now(), version='5.1').save()
        loop = asyncio.new_event_loop()  # 或 loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(loop)
        t1 = threading.Thread(target=req.AsyncScore(), args=())
        t2 = threading.Thread(target=req.getRank(), args=())
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    try:
        process()
        gpa = req.score
        rank = req.rank
        if gpa is None or rank is None:
            return JsonResponseUtf8({}, 500, False, "请求失败")
        return JsonResponseUtf8({
            "gpa": gpa,
            "rank": rank
        }, 200, True, "登录成功")
    except func_timeout.exceptions.FunctionTimedOut:
        return JsonResponseUtf8({}, 500, False, "网络拥挤，稍后再试")
    except Exception as e:
        return JsonResponseUtf8({}, 500, False, str(e))
    finally:
        req.session.session.close()
        del req


def getScoreDebug(request):
    if request.method != 'POST':
        return JsonResponseUtf8({}, 405, False, "方法不允许")
    username = request.POST.get("username")
    password = request.POST.get("password")
    forbidden = Forbidden.objects.filter(username=username).first()
    if forbidden is not None:
        return JsonResponseUtf8({}, 403, False, "禁止访问")
    else:
        if Forbidden.objects.filter(username='*').first():
            return JsonResponseUtf8({}, 403, False, "暂时不允许访问 Service Temporarily Unavailable")

    standby = Standby.objects.filter(username=username).first()
    white = White.objects.filter(username=username).first()
    if standby is not None and white is None:
        t1 = standby.loginTime.timestamp()
        t2 = timezone.now().timestamp()
        delta = t2 - t1
        bet = standby.between
        if delta < bet:
            stand = bet - delta
            return JsonResponseUtf8({}, 502, False, "距离下一次访问还需" + getStandTime(stand))

    req = Req({
        "username": username,
        "password": password,
    })

    # @func_set_timeout(20)
    def process():
        login = req.login()
        if login is None:
            return JsonResponseUtf8({}, 404, False, "账号或密码错误")
        print('login')
        LoginInfo(username=username, loginTime=timezone.now(), version='5.1').save()
        loop = asyncio.new_event_loop()  # 或 loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(loop)
        t1 = threading.Thread(target=req.AsyncScore(), args=())
        t2 = threading.Thread(target=req.getRank(), args=())
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    try:
        process()
        gpa = req.score
        rank = req.rank
        if gpa is None or rank is None:
            return JsonResponseUtf8({}, 500, False, "请求失败")
        if standby is not None:
            standby.delete()
        bet = random.randint(15 * 60, 25 * 60)
        Standby(username=username, loginTime=timezone.now(), between=bet).save()
        return JsonResponseUtf8({
            "gpa": gpa,
            "rank": rank
        }, 200, True, "登录成功")
    except func_timeout.exceptions.FunctionTimedOut:
        return JsonResponseUtf8({}, 500, False, "网络拥挤，稍后再试")
    except Exception as e:
        msg = traceback.format_exc()
        return JsonResponseUtf8({}, 500, False, str(e) + msg)
    finally:
        logout = 'https://uis.nwpu.edu.cn/cas/logout'
        req.session.get(logout)
        req.session.session.close()
        del req


def getData(username, req):
    login = req.login()
    print(login)
    if login is None:
        return JsonResponseUtf8({}, 404, False, "账号或密码错误")
    print('login')
    LoginInfo(username=username, loginTime=timezone.now(), version='5.1').save()
    print("get loop")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("AsyncScore get")
    req.AsyncScore()
    # t1 = threading.Thread(target=, args=())
    t2 = threading.Thread(target=req.getRank(), args=())
    # t1.start()
    t2.start()
    # t1.join()
    t2.join()

    # user = Score.objects.filter(username=username).first()

    def dumps(obj):
        return json.dumps(obj, ensure_ascii=False)

    # if user is None:
    #     user = Score(username=username, gpa=dumps(req.score), rank=dumps(req.rank))
    #     user.save()
    # else:
    #     user.delete()
    #     user = Score(username=username, gpa=dumps(req.score), rank=dumps(req.rank))
    #     user.save()


def verify(request):
    if request.method != 'POST':
        return JsonResponseUtf8({}, 405, False, "方法不允许")
    if request.session.get("gid") is None:
        return JsonResponseUtf8({}, 404, False, "不存在gid")

    mfa_code = request.POST.get("code")
    if mfa_code is None:
        return JsonResponseUtf8({}, 404, False, "mfa_code必须")
    username = request.session.get("username")
    password = request.session.get("password")
    gid = request.session['gid']
    mfa = request.session['mfa']
    validURL = "https://uis.nwpu.edu.cn/attest/api/guard/securephone/valid"
    res = json.loads(requests.post(validURL, headers={
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 Edg/106.0.1370.37"
    }, json={"gid": gid, "code": mfa_code}).content.decode("utf-8"))["data"]
    print(res)
    if res["status"] != 2:
        return JsonResponseUtf8({}, 400, False, "验证失败")

    forbidden = Forbidden.objects.filter(username=username).first()
    if forbidden is not None:
        return JsonResponseUtf8({}, 403, False, "禁止访问")
    else:
        if Forbidden.objects.filter(username='*').first():
            return JsonResponseUtf8({}, 403, False, "暂时不允许访问 Service Temporarily Unavailable")

    standby = Standby.objects.filter(username=username).first()
    white = White.objects.filter(username=username).first()
    if standby is not None and white is None:
        t1 = standby.loginTime.timestamp()
        t2 = timezone.now().timestamp()
        delta = t2 - t1
        bet = standby.between
        if delta < bet:
            stand = bet - delta
            return JsonResponseUtf8({}, 502, False, "距离下一次访问还需" + getStandTime(stand))

    req = Req({
        "username": username,
        "password": password,
    }, gid=gid, mfa=mfa)

    @func_set_timeout(20)
    def process():
        getData(username=username, req=req)
        return {
            "success": True
        }

    try:
        print("getting")
        # login = req.login()
        # print(login)

        getData(username=username, req=req)
        gpa = req.score
        rank = req.rank
        if gpa is None or rank is None:
            return JsonResponseUtf8({}, 500, False, "请求失败")
        if standby is not None:
            standby.delete()
        bet = random.randint(15 * 60, 25 * 60)
        Standby(username=username, loginTime=timezone.now(), between=bet).save()
        return JsonResponseUtf8({
            "gpa": gpa,
            "rank": rank
        }, 200, True, "登录成功")
    except func_timeout.exceptions.FunctionTimedOut:
        return JsonResponseUtf8({}, 500, False, "网络拥挤，稍后再试")
    except Exception as e:
        msg = traceback.format_exc()
        return JsonResponseUtf8({}, 500, False, str(e) + msg)
    finally:
        logout = 'https://uis.nwpu.edu.cn/cas/logout'
        req.session.get(logout)
        req.session.session.close()
        del req


def loginMFA(request):
    if request.method != 'POST':
        return JsonResponseUtf8({}, 405, False, "方法不允许")
    username = request.POST.get("username")
    password = request.POST.get("password")

    if username == '' and password == '':
        request.session['username'] = username
        request.session['password'] = password
        request.session['admin'] = True
        # users_all = Score.objects.all()
        users_all = []
        users = []
        for u in users_all:
            users.append(u.username)

        classfied_strings = {}
        for string in users:
            key = string[:4]
            if key in classfied_strings:
                classfied_strings[key].append(string)
            else:
                classfied_strings[key] = [string]
        users = list(classfied_strings.values())
        return JsonResponseUtf8({"users": users}, 1001, True, "Admin Login")

    forbidden = Forbidden.objects.filter(username=username).first()
    if forbidden is not None:
        return JsonResponseUtf8({}, 403, False, "禁止访问")
    else:
        if Forbidden.objects.filter(username='*').first():
            return JsonResponseUtf8({}, 403, False, "暂时不允许访问 Service Temporarily Unavailable")

    standby = Standby.objects.filter(username=username).first()
    white = White.objects.filter(username=username).first()
    if standby is not None and white is None:
        t1 = standby.loginTime.timestamp()
        t2 = timezone.now().timestamp()
        delta = t2 - t1
        bet = standby.between
        if delta < bet:
            stand = bet - delta
            return JsonResponseUtf8({}, 502, False, "距离下一次访问还需" + getStandTime(stand))

    req = Req({
        "username": username,
        "password": password,
    })
    need = req.getMfa()
    if need:
        send = req.send()
        request.session['username'] = username
        request.session['password'] = password
        request.session['gid'] = req.gid
        request.session['mfa'] = req.mfa
        return JsonResponseUtf8({
            "securePhone": send["securePhone"]
        }, 304, False, "填写您接收到的短信验证码")

    @func_set_timeout(20)
    def process():
        getData(username=username, req=req)
        return {
            "success": True
        }

    try:
        rtn = process()
        gpa = req.score
        rank = req.rank
        if gpa is None or rank is None:
            return JsonResponseUtf8({}, 500, False, "请求失败")
        if standby is not None:
            standby.delete()
        bet = random.randint(15 * 60, 25 * 60)
        Standby(username=username, loginTime=timezone.now(), between=bet).save()
        return JsonResponseUtf8({
            "gpa": gpa,
            "rank": rank
        }, 200, True, "登录成功")
    except func_timeout.exceptions.FunctionTimedOut:
        return JsonResponseUtf8({}, 500, False, "网络拥挤，稍后再试")
    except Exception as e:
        msg = traceback.format_exc()
        return JsonResponseUtf8({}, 500, False, str(e) + msg)
    finally:
        # logout = 'https://uis.nwpu.edu.cn/cas/logout'
        # req.session.get(logout)
        req.session.session.close()
        del req


def getUserScore(request):
    if request.method != 'POST':
        return JsonResponseUtf8({}, 405, False, "方法不允许")
    if request.session.get("admin") is None or not request.session.get("admin"):
        return JsonResponseUtf8({}, 404, False, "没有权限")

    username = request.session.get("username")
    password = request.session.get("password")

    if username is None or password is None or \
            username != "" or password != "":
        return JsonResponseUtf8({}, 404, False, "未登录")

    find = request.POST.get("username")

    if find is None:
        return JsonResponseUtf8({}, 500, False, "参数不合法")

    try:
        return JsonResponseUtf8({
            "gpa": [],
            "rank": {
                "studentAssoc": 265695,
                "rank": 15,
                "gpa": 3.889,
                "beforeRankGpa": 3.892,
                "afterRankGpa": 3.881,
                "avgMajorGpa": 3.509,
                "num": [
                    18,
                    206,
                    9,
                    3,
                    1,
                    237
                ]
            }
        }, 200, True, find + "查询成功")
        # score = Score.objects.get(username=find)
        # return JsonResponseUtf8({
        #     "gpa": json.loads(score.gpa),
        #     "rank": json.loads(score.rank)
        # }, 200, True, find + "查询成功")
    except Exception as e:
        msg = traceback.format_exc()
        return JsonResponseUtf8({}, 500, False, str(e) + msg)


def getStandTime(t: int) -> str:
    if t < 60:
        return str(int(t)) + "s"
    m = int(t / 60)
    s = int(t - m * 60)
    return str(m) + "m" + str(s) + "s"


def decryption(text_encrypted_base64: str, private_key: bytes):
    text_encrypted_base64 = text_encrypted_base64.encode('utf-8')
    text_encrypted = base64.b64decode(text_encrypted_base64)
    cipher_private = PKCS1_v1_5.new(RSA.importKey(private_key))
    text_decrypted = cipher_private.decrypt(text_encrypted, Random.new().read)
    text_decrypted = text_decrypted.decode()
    return text_decrypted


def feedback(request):
    if request.method != 'POST':
        return JsonResponseUtf8({}, 405, False, "方法不允许")
    try:
        rate = request.POST.get('rate')
        message = request.POST.get('message')
        sendTime = timezone.now()
        Feedback(rate=rate, message=message, sendTime=sendTime).save()
        return JsonResponseUtf8({}, 200, True, "反馈已收到，感谢您的支持！")
    except Exception as e:
        return JsonResponseUtf8({}, 500, False, str(e))


def JsonResponseUtf8(data, code: int, success: bool, message: str):
    rtn = {
        "data": data,
        "code": code,
        "success": success,
        "message": message
    }
    return HttpResponse(
        json.dumps(rtn, ensure_ascii=False),
        content_type="application/json,charset=utf-8"
    )
