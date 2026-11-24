import logging
import time
import requests
log = logging.getLogger(__name__)
class RequestUtil:
    def __init__(self, base_url, timeout=(3, 5)):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.token = None
        self.username = None
        self.password = None

    def get(self, path, **kwargs):
        return self.request('GET', path, **kwargs)

    def post(self, path, **kwargs):
        return self.request('POST', path, **kwargs)

    def request(self, method, path, authorized=False, _retry_auth=True,_retry_429=2, **kwargs):
        url = self.base_url + path
        kwargs.setdefault('timeout', self.timeout)
        start=time.perf_counter()
        headers = kwargs.pop('headers',{})or {}
        if authorized:
            if not self.token:
                self.login(self.username, self.password)
            if not self.token:
                log.error('<--登录失败，拿不到token，放弃请求url=%s',url)
                return None
            headers["Authorization"] = "Bearer " + self.token

        kwargs['headers'] = headers
        log.info('<-- %s %s  ', method.upper(), url)
        try:
            res = self.session.request(method, url, **kwargs)
            log.info('<-- %s %s 耗时=%.0fms 状态码：%s',method.upper(),url,(time.perf_counter()-start)*1000,res.status_code)

        except requests.exceptions.ConnectTimeout:
            log.error('<--连接超时 url=%s 耗时=%.0fms',url,(time.perf_counter()-start)*1000)
            return None
        except requests.exceptions.ReadTimeout:
            log.error('<--读取超时 url=%s timeout=%s,耗时=%.0fms',url ,kwargs['timeout'],(time.perf_counter()-start)*1000)
            return None
        except requests.RequestException as e:
            log.error('<-- 请求异常 %s,耗时=%.0fms',e,(time.perf_counter()-start)*1000)
            return None
        if res.status_code == 401 and _retry_auth and authorized:
            log.warning('<--收到401，token可能过期，重新登录后重试一次，url=%s',url)
            self.token=None
            self.login(self.username,self.password)
            return self.request(method, path, authorized=authorized,_retry_auth=False,_retry_429=_retry_429 ,**kwargs)
        if (res.status_code == 429 and _retry_429 > 0 and method.upper()in ('HEAD','GET','PUT','DELETE','OPTIONS')):
            try:
                wait=float(res.headers.get('Retry-After','1'))
            except ValueError:
                wait=1.0
            wait=min(wait,5)
            log.warning('<--收到429限流，%.1f秒后重试 url=%s',wait,url)
            time.sleep(wait)
            return self.request(method, path, **kwargs,authorized=authorized,_retry_429=_retry_429-1,_retry_auth=_retry_auth)
        return res
    def login(self, username, password):
        self.username = username
        self.password = password
        res=self.post('/login', json={'username':username, 'password':password})
        if  res is None:
            log.error('<--登录请求失败，没有拿到响应')
            return False
        if res.status_code != 200:
            log.error('<--登录HTTP异常，状态码=%s',res.status_code)
            return False
        body = res.json()
        if body.get('code') !=0:
            log.error('<--登录业务失败 code=%s msg=%s',body.get('code'),body.get('msg'))
            return False
        token=(body.get('data')or{}).get('token')
        if not token :
            log.error('<--响应里没有token：%s',body)
            return False
        self.token = token
        log.info('登录成功，token已保存')
        return True
    def close(self):
        self.session.close()