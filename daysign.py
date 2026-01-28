import os
import re
import json
import time
import httpx
import traceback
import random
from contextlib import contextmanager
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET
from captcha import resolve_captcha, CaptchaError
from flaresolverr import FlareSolverrHTTPClient

SEHUATANG_HOST = 'www.sehuatang.net'
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'

FID = 103  # 高清中文字幕

REPLY_TIMES = os.getenv('REPLY_TIMES_98TANG', 1)

AUTO_REPLIES = (
    '感谢楼主分享好片',
    '感谢分享！！',
    '谢谢分享！',
    '感谢分享感谢分享',
    '必需支持',
    '简直太爽了',
    '感谢分享啊',
    '封面还不错',
    '有点意思啊',
    '封面还不错，支持一波',
    '真不错啊',
    '不错不错',
    '这身材可以呀',
    '终于等到你',
    '不错。。！',
    '謝謝辛苦分享',
    '赏心悦目',
    '快乐无限~~',
    '這怎麼受的了啊',
    '谁也挡不住！',
    '感謝分享',
    '分享支持。',
    '这谁顶得住啊',
    '这是要精J人亡啊！',
    '饰演很赞',
    '這系列真有戲',
    '感谢大佬分享',
    '看着不错',
    '感谢老板分享',
    '可以看看',
    '谢谢分享！！！',
    '真是骚气十足',
    '给我看硬了！',
    '这个眼神谁顶得住。',
    '妙不可言',
    '看硬了，确实不错。',
    '等这一部等了好久了！',
    '终于来了，等了好久了。',
    '这一部确实不错',
    '感谢分享这一部资源',
    '剧情还是挺OK的。',
)


def daysign(
    cookies: dict,
    flaresolverr_url: str = None,
    flaresolverr_proxy: str = None,
) -> bool:

    with (FlareSolverrHTTPClient(url=flaresolverr_url,
                                 proxy_url=flaresolverr_proxy,
                                 cookies=cookies,
                                 http2=True)
          if flaresolverr_url else httpx.Client(cookies=cookies, http2=True)) as client:

        @contextmanager
        def _request(method, url, *args, **kwargs):
            r = client.request(method=method, url=url,
                               headers={
                                   'user-agent': DEFAULT_USER_AGENT,
                                   'dnt': '1',
                                   'accept': '*/*',
                                   'sec-ch-ua-mobile': '?0',
                                   'sec-ch-ua-platform': 'macOS',
                                   'sec-fetch-site': 'same-origin',
                                   'sec-fetch-mode': 'cors',
                                   'sec-fetch-dest': 'empty',
                                   'referer': f'https://{SEHUATANG_HOST}/plugin.php?id=dd_sign',
                                   'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
                               }, *args, **kwargs)
            try:
                r.raise_for_status()
                yield r
            finally:
                r.close()

        # age verification
        age_confirmed = False
        age_retry_cnt = 3
        while not age_confirmed and age_retry_cnt > 0:
            with _request(method='get', url=f'https://{SEHUATANG_HOST}/') as r:
                if (v := re.findall(r"safeid='(\w+)'",
                                    r.text, re.MULTILINE | re.IGNORECASE)) and (safeid := v[0]):
                    print(f'set age confirm cookie: _safe={safeid}')
                    client.cookies.set(name='_safe', value=safeid)
                else:
                    age_confirmed = True
                age_retry_cnt -= 1

        if not age_confirmed:
            raise Exception('failed to pass age confirmation')

        # find TIDs from the given FID
        with _request(method='get', url=f'https://{SEHUATANG_HOST}/forum.php?mod=forumdisplay&fid={FID}') as r:
            tids = re.findall(r"normalthread_(\d+)", r.text,
                              re.MULTILINE | re.IGNORECASE)
            print(f'all tids found: {tids}')

        # Post comments to forums
        for _ in range(int(REPLY_TIMES)):

            tid = random.choice(tids)
            print(f'choose tid = {tid} to comment')

            with _request(method='get', url=f'https://{SEHUATANG_HOST}/forum.php?mod=viewthread&tid={tid}&extra=page%3D1') as r:
                soup = BeautifulSoup(r.text, 'html.parser')
                formhash = soup.find('input', {'name': 'formhash'})['value']
                print(f'formhash found for tid={tid}: {formhash}')

            message = random.choice(AUTO_REPLIES)

            with _request(method='post', url=f'https://{SEHUATANG_HOST}/forum.php?mod=post&action=reply&fid={FID}&tid={tid}&extra=page%3D1&replysubmit=yes&infloat=yes&handlekey=fastpost&inajax=1',
                          data={
                              'file': '',
                              'message': message,
                              'posttime': int(time.time()),
                              'formhash': formhash,
                              'usesig': '',
                              'subject': '',
            }) as r:
                print(f'commented to: tid = {tid}, message = {message}')
                # print(r.text)

            time.sleep(random.randint(16, 20))

        # access the day sign page, but do nothing
        with _request(method='get', url=f'https://{SEHUATANG_HOST}/plugin.php?id=dd_sign') as r:
            # id_hash_rsl = re.findall(
            #     r"updatesecqaa\('(.*?)'", r.text, re.MULTILINE | re.IGNORECASE)
            # id_hash = id_hash_rsl[0] if id_hash_rsl else 'qS0'  # default value

            # soup = BeautifulSoup(r.text, 'html.parser')
            # formhash = soup.find('input', {'name': 'formhash'})['value']
            # signtoken = soup.find('input', {'name': 'signtoken'})['value']
            # action = soup.find('form', {'name': 'login'})['action']
            pass

        def _decode_json_from_resp(r):
            try:
                data = r.json()
            except json.decoder.JSONDecodeError:
                # print(f"try parse and load JSON: {r.text}")
                soup = BeautifulSoup(r.text, "html.parser")
                body_text = soup.body.get_text(strip=True)
                data = json.loads(body_text)
            return data

        def _load_captcha():
            time.sleep(random.randint(5, 8))  # rate limit on captcha loading
            with _request(method='get', url=f'https://{SEHUATANG_HOST}/misc.php?mod=captcha') as r:
                captcha = _decode_json_from_resp(r)
                return captcha

        def _submit_captcha(value: str):
            time.sleep(random.randint(2, 3))
            with _request(method='post', url=f'https://{SEHUATANG_HOST}/misc.php?mod=captcha&action=check', data=value) as r:
                data = _decode_json_from_resp(r)
                return data

        def _do_sign():
            time.sleep(random.randint(0, 1))
            with _request(method='get', url=f'https://{SEHUATANG_HOST}/plugin.php?id=dd_sign&ac=sign_v2') as r:
                captcha = _decode_json_from_resp(r)
                return captcha

        maxRetries = 6
        for retry in range(maxRetries):
            captcha = _load_captcha()

            # save captcha data for debugging
            # with open("captcha_debug.json", "+w") as f:
            #     json.dump(captcha, f)

            try:
                print(
                    f'try #{retry} captcha solving: type={captcha["data"]["type"]}')
            except:
                print(f'load captcha error: {captcha}')
                return  # stop retrying

            try:
                ans = resolve_captcha(captcha)
                print(f"resolved answer: {ans}")
                data = _submit_captcha(ans)
                print(f'submitted answer: {data}')
                match data.get("data"):
                    case "ok":
                        data = _do_sign()
                        print(f'daysign requested: {data}')
                        return data
                    case "failure":
                        # failed, maybe try again
                        print(f'captcha resolving failed, try again')
                        continue
            except CaptchaError as e:
                print(f"captcha error: {e}")
                continue

            return  # stop retrying


def retrieve_cookies_from_curl(env: str) -> dict:
    cURL = os.getenv(env, '').replace('\\', ' ')
    try:
        import uncurl
        return uncurl.parse_context(curl_command=cURL).cookies
    except ImportError:
        print("uncurl is required.")


def retrieve_cookies_from_fetch(env: str) -> dict:
    def parse_fetch(s: str) -> dict:
        ans = {}
        exec(s, {
            'fetch': lambda _, o: ans.update(o),
            'null': None
        })
        return ans
    cookie_str = parse_fetch(os.getenv(env))['headers']['cookie']
    return dict(s.strip().split('=', maxsplit=1) for s in cookie_str.split(';'))


def preprocess_text(text) -> str:
    if 'xml' not in text:
        return text

    try:
        root = ET.fromstring(text)
        cdata = root.text
        soup = BeautifulSoup(cdata, 'html.parser')
        for script in soup.find_all('script'):
            script.decompose()
        return soup.get_text()
    except:
        return text


def push_notification(title: str, content: str) -> None:

    def telegram_send_message(text: str, chat_id: str, token: str, silent: bool = False) -> None:
        r = httpx.post(url=f'https://api.telegram.org/bot{token}/sendMessage',
                       json={
                           'chat_id': chat_id,
                           'text': text,
                           'disable_notification': silent,
                           'disable_web_page_preview': True,
        })
        r.raise_for_status()

    try:
        from notify import telegram_bot
        telegram_bot(title, content)
    except ImportError:
        chat_id = os.getenv('TG_USER_ID')
        bot_token = os.getenv('TG_BOT_TOKEN')
        if chat_id and bot_token:
            telegram_send_message(f'{title}\n\n{content}', chat_id, bot_token)


def main():

    results = None
    cookies = {}

    if os.getenv('FETCH_98TANG'):
        cookies = retrieve_cookies_from_fetch('FETCH_98TANG')
    elif os.getenv('CURL_98TANG'):
        cookies = retrieve_cookies_from_curl('CURL_98TANG')

    try:
        results = daysign(
            cookies=cookies,
            flaresolverr_url=os.getenv('FLARESOLVERR_URL'),
            flaresolverr_proxy=os.getenv('FLARESOLVERR_PROXY'),
        )

        message = results['message']

        if '签到成功' in message:
            title, message_text = '98堂 每日签到', message
        elif '重复签到' in message:
            title, message_text = '98堂 每日签到', message
        elif '需要先登录' in message:
            title, message_text = '98堂 签到异常', f'Cookie无效或已过期，请重新获取'
        else:
            title, message_text = '98堂 签到异常', message
    except Exception as e:
        title, message_text = '98堂 签到异常', f'错误原因：{e}'
        # log detailed error message
        traceback.print_exc()

    # process message data
    message_text = preprocess_text(message_text)

    # log to output
    print(message_text)

    # telegram notify
    push_notification(title, message_text)


if __name__ == '__main__':
    main()
