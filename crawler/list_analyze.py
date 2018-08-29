import re
import time
from misc.config import config
if __name__ == '__main__':
    from crawler.common import load_page
else:
    from .common import load_page


def format_code_dcinside(code, recommend=False):
    ret = 'http://gall.dcinside.com/board/lists/?id=' + code
    soup = load_page(ret)
    mat = re.match("window.location.replace\('(?P<target>\S+)'\);", soup.text)
    if bool(mat):
        ret = 'http://gall.dcinside.com' + mat.group('target')

    ret += '&page=1'
    if recommend:
        ret += '&exception_mode=recommend'

    return ret


def find_gall(keyword):
    search_url = 'http://m.dcinside.com/search/index.php?search_gall={}&search_type=gall_name'.format(keyword)
    soup = load_page(search_url, mobile=True, extra_headers={'Host': 'm.dcinside.com'})

    ret = []
    a_list = soup.find('div', class_="searh-result-box").find_all('a')
    for a in a_list:
        if 'http://m.dcinside.com/list.php' in a.get('href'):
            title = ''.join(a.strings).strip()
            code = re.split('=', a.get('href'))[1]
            ret.append([title, code])
    return ret

    
class ListBot(object):
    def __init__(self, url):
        self.url = url
        self.last_list = 0
        self.title = ''
        self.target_index_range = []
        self.target_page_range = []

    def get_last_list(self):
        pass

    def _parse_range_input(self, input_value):
        if self.last_list == 0:
            raise IOError

        if not bool(re.match('^[\d, \-]+$', input_value)):  # 선택 범위에 숫자, - , , 외 다른 게 있으면 거부
            raise IOError

        page_list = []
        range_split_list = input_value.split(',')
        for p in range_split_list:  # 1-4, 10 ==> [1, 2, 3, 4, 10]
            value = p.strip()
            if '-' in value:
                init, fin = [int(x) for x in value.split('-')]
                page_list += list(range(init, fin + 1))
            else:
                page_list.append(int(value))

        page_list = set(page_list)
        full_page_range = set(range(1, self.last_list + 1))
        if not (page_list < full_page_range or page_list == full_page_range):
            raise IOError

        else:
            self.target_index_range = list(page_list)

    def get_target_pages(self, input_value):
        pass


class DCInsideList(ListBot):
    def __init__(self, code, recommend=True, keyword_filter=False):
        super(DCInsideList, self).__init__(code)
        self.recommend = recommend
        self.code = code
        self.url = format_code_dcinside(self.code, self.recommend)
        if not keyword_filter:
            self.keyword_filter = []
        else:
            self.keyword_filter = config.value['Filter']['Keyword'].split(config.value['Filter']['Parser'])

        self.target_page_range = []

    def get_last_list(self):
        soup = load_page(self.url)
        self.title = soup.title.string.strip()
        if self.recommend:
            self.title += ' (개념글만)'

        page_range_tag = soup.find('div', id='dgn_btn_paging')
        end_page_url = page_range_tag.find_all('a')[-1].get('href')
        last_page_mat = re.search('page=(?P<pagenum>\d+)', end_page_url)
        if bool(last_page_mat):  # 마지막 페이지가 있는 경우
            self.last_list = int(last_page_mat.group('pagenum'))
        else:  # 마지막 페이지가 없는 경우
            self.last_list = 1

    def _parse_one_list(self, article_list):
        soup = load_page(article_list)
        threads = soup.find('tbody', attrs={'class', 'list_tbody'}).find_all('tr')  # 각 tr 항목마다 갤 제목 등등 저장

        valid_threads = []
        for t in threads:
            if t.find('td') is None:
                continue
            header = t.find('td', class_='t_notice').string
            if bool(re.match('\d+', header)):  # 공지사항 등 제외
                valid_threads.append(t)

        if len(self.keyword_filter) == 0:  # 제목 필터 없는 경우
            ret = ['http://gall.dcinside.com' + v.find('a').get('href') for v in valid_threads]

        else:  # 제목 필터 적용
            ret = []
            for v in valid_threads:
                thread_title = ''.join(v.find('td', class_='t_subject').strings)
                for k in self.keyword_filter:
                    if k in thread_title:
                        ret.append('http://gall.dcinside.com' + v.find('a').get('href'))
                        break

        return ret

    def get_target_pages(self, input_value):
        self._parse_range_input(input_value)
        for list_page_num in self.target_index_range:
            list_page = self.url + '&page={}'.format(list_page_num)
            if self.recommend:  # 개념글만
                list_page += '&exception_mode=recommend'
            self.target_page_range += self._parse_one_list(list_page)

        return self.target_page_range


class TistoryList(ListBot):
    def __init__(self, url):
        if not url.startswith('http://'):
            url = 'http://' + url
        if not url.endswith('/?'):
            url += '/?'
        super(TistoryList, self).__init__(url)

    def get_last_list(self):
        title_soup = load_page(self.url)
        mat = re.search('\S+.src="(?P<prefix>\S+)"\+Date.now\(\)\+"(?P<suffix>\S+)"', title_soup.text)
        if bool(mat):
            new_referer = mat.group('prefix') + str(round(time.time())) + mat.group('suffix')
            title_soup = load_page(self.url, extra_headers={'Referer': new_referer})
        self.title = title_soup.title.string.strip()

        category_soup = load_page(self.url + 'category')
        url_list = []
        a_list = category_soup.find_all('a')
        for a in a_list:
            link = a.get('href')
            if link is not None:
                mat = re.search('^/(?P<page_id>\d+)', a.get('href'))
                if bool(mat):
                    url_list.append(int(mat.group('page_id')))

        self.last_list = max(url_list)

    def get_target_pages(self, input_value):
        self.get_last_list()
        self._parse_range_input(input_value)
        self.target_page_range = [self.url.replace('?', str(i)) for i in self.target_index_range]

        return self.target_page_range


class NaverPostList(ListBot):
    def __init__(self, url):
        if not url.startswith('http://'):
            url = 'http://' + url
        super(NaverPostList, self).__init__(url)

    def get_last_list(self):
        soup = load_page(self.url)
        self.title = soup.find('h2', {'class': 'tit_series'}).string
        a_list = soup.find_all('a', {'class': 'spot_post_area'})
        self.last_list = len(a_list)

    def get_target_pages(self, input_value):
        self.get_last_list()
        self._parse_range_input(input_value)

        self.target_page_range = [self.url + '/' + str(i) for i in self.target_index_range]

        return self.target_page_range


def find_bot(url):
    if 'gall.dcinside.com' in url:
        return DCInsideList
    elif 'naver.com' in url:
        return NaverPostList
    else:
        return TistoryList
