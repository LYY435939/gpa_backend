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
