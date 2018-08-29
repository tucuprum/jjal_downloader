import re
from urllib import parse as urlparse
import requests
from bs4 import BeautifulSoup

MOBILE_UA = ('Mozilla/5.0 (Linux; U; Android 2.1-update1; ko-kr; Nexus One Build/ERE27) AppleWebKit/530.17 '
             '(KHTML, like Gecko) Version/4.0 Mobile Safari/530.17')
DESKTOP_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 '
              'Safari/537.36 Edge/17.17134')


def refine_url(url):  # refine raw urls into requests-safe ones
    if 'http://' not in url and 'https://' not in url:
        url = 'http://' + url

    m = re.match('http://(?P<naverid>\S+).blog.me/(?P<logNo>\d+)', url)
    if bool(m):
        url = 'http://blog.naver.com/PostView.nhn?blogId=' + m.group('naverid') + '&logNo=' + m.group('logNo')
    else:
        m2 = re.match('http://blog.naver.com/(?P<naverid>\S+)/(?P<logNo>\d+)', url)
        if bool(m2):
            url = 'http://blog.naver.com/PostView.nhn?blogId=' + m2.group('naverid') + '&logNo=' + m2.group('logNo')
    url_safe_chars = '&$+,/:;=?@#'

    return urlparse.quote(url, safe=url_safe_chars, encoding='utf-8')


def load_page(url, make_soup=True, mobile=False, extra_headers=None):
    # input: url string ==> output:BeautifulSoup (preferred for dcinside: it checks the referer)
    try:
        with requests.session() as s:
            s.headers['Accept'] = 'text/html, application/xhtml+xml, image/jxr, */*'
            s.headers['Accept-Encoding'] = 'gzip, deflate'
            s.headers['Connection'] = 'Keep-Alive'
            s.headers['User-Agent'] = MOBILE_UA if mobile else DESKTOP_UA
            if 'dcinside.com' in url:
                s.headers['Accept-Language'] = 'ko-KR'
                s.headers['Host'] = 'gall.dcinside.com'
            else:
                s.headers['Accept-Language'] = 'ko, en-US; q=0.7, en; q=0.3'
                s.headers['Host'] = urlparse.urlparse(url).netloc

            if extra_headers is not None:
                for key in extra_headers.keys():
                    s.headers[key] = extra_headers[key]

            html = s.get(url).text

        if make_soup:
            soup = BeautifulSoup(html, 'lxml')
            return soup
        else:
            return html
    except:
        return None