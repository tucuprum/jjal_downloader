import re
from bs4 import BeautifulSoup
if __name__ == '__main__':
    from crawler.common import load_page
else:
    from .common import load_page


class PageBot(object):
    def __init__(self, url: str):
        self.url = url
        self.soup = None  # type: BeautifulSoup
        self._raw_title = None  # type: str
        self.title = None  # type: str
        self.images = []

    def read_page(self):
        pass

    def _get_raw_title(self):
        self._raw_title = str(self.soup.title.string.encode('euc-kr', 'ignore').decode('euc-kr')).strip()

    def _get_soup(self):
        self.soup = load_page(self.url)
        self._get_raw_title()


class DCInsdePage(PageBot):  # 'dcinside.com' in url
    def __init__(self, url):
        super(DCInsdePage, self).__init__(url)

    def read_page(self):
        self._get_soup()
        self.title = self._raw_title

        # files from attachments
        file_nos = {}
        attached_tag_raw = self.soup.find('ul', class_='appending_file')
        if attached_tag_raw is not None:
            attached_tags = attached_tag_raw.find_all('a')
            for file in attached_tags:
                file_url = file.get('href')
                url_mat = re.search('php\?id=\S+&no=(?P<imgid>\S+)&f_no', file_url)
                if bool(url_mat):
                    img_id = url_mat.group('imgid')
                    file_nos[img_id] = file_url

        # files from main contents
        cont = self.soup.find('div', attrs={'class', 's_write'})
        a_tags = cont.find_all('a', target='image')

        if len(a_tags) > 0:
            for a in a_tags:
                img_url = a.get('href')
                normal_upload = re.search('php\?id=\S+&no=(?P<imgid>\S+)', img_url)
                if bool(normal_upload):
                    img_id = normal_upload.group('imgid')
                    if img_id in file_nos:
                        self.images.append(file_nos[img_id])
                    else:
                        self.images.append(img_url)
                else:
                    self.images.append(img_url)

        else:
            img_tags = cont.find_all('img')
            for img_tag in img_tags:
                img_tag_str = str(img_tag)
                if 'dccon.php' in img_tag_str:  # 디시콘 제외
                    continue

                if 'imgPop' in img_tag_str:
                    orig_tag_script = img_tag.get('onclick')
                    mat = re.search("javascript:imgPop\('(?P<address>\S+)','image'", orig_tag_script)
                    if bool(mat):
                        img_url = mat.group('address')
                    else:
                        img_url = orig_tag_script.split('onclick')[1].replace('Pop', '')
                    img_id = re.search('&no=(?P<imgid>\w+)', img_url).group('imgid')
                    if img_id in file_nos:
                        self.images.append(file_nos[img_id])
                    else:
                        self.images.append(img_url)

                elif img_tag.get('src').startswith('http://') or img_tag.get('src').startswith('https://'):
                    img_url = img_tag.get('src')
                    mat = re.search('php\?id=\S+&no=(?P<imgid>\S+)', img_url)
                    if bool(mat):
                        img_id = mat.group('imgid')
                        if img_id in file_nos:
                            self.images.append(file_nos[img_id])
                    else:
                        self.images.append(img_url)


class NaverBlogPage(PageBot):  # 'blog.naver.com' in url
    def __init__(self, url):
        super(NaverBlogPage, self).__init__(url)

    def read_page(self):
        self._get_soup()
        self.title = self._raw_title

        img_tags = self.soup.find_all('img')
        for img_tag in img_tags:
            raw_url = re.sub('postfiles\d+', 'blogfiles', img_tag.get('src'))
            if '.png' in raw_url or '.jpg' in raw_url:
                img_url = raw_url.split('?type=')[0]
                self.images.append(img_url)


class NaverPostPage(PageBot):  # 'post.naver.com' in url
    def __init__(self, url):
        super(NaverPostPage, self).__init__(url)

    def read_page(self):
        self._get_soup()
        self.title = self._raw_title.replace(': 네이버 포스트', '').strip().replace('\n', ' ')

        main_div = self.soup.find('div', {'id': 'cont', 'class': ['end', '__viewer_container']})
        img_tags = BeautifulSoup(main_div.script.string, 'lxml').find_all('img')

        for img_tag in img_tags:
            img_url = img_tag.get('data-src')
            if img_url.startswith('https://storep-phinf.pstatic.net/'):  # naver 이모티콘 제외
                continue

            srch = re.search('\?type=\S+$', img_url)  # ?type=w1200 같이 마지막에 붙는 이미지 크기 변수 제거
            if bool(srch):
                self.images.append(img_url.replace(srch.group(), ''))
            else:
                self.images.append(img_url)


class NaverNews(PageBot):  # 'entertain.naver.com' in url
    def __init__(self, url):
        super(NaverNews, self).__init__(url)

    def read_page(self):
        self._get_soup()
        self.title = self._raw_title.replace(':: 네이버 TV연예', '').replace('\n', ' ').strip()

        cont = self.soup.find('div', {'id': 'articeBody'})
        for img_tag in cont.find_all('img'):
            img = img_tag.get('src')
            srch = re.search('\?type=\S+$', img)  # ?type=w1200 같이 마지막에 붙는 이미지 크기 변수 제거
            if bool(srch):
                self.images.append(img.replace(srch.group(), ''))
            else:
                self.images.append(img)


class InstagramPage(PageBot):  # 'instagram.com' in url
    def __init__(self, url):
        super(InstagramPage, self).__init__(url)

    def read_page(self):
        self._get_soup()
        match_owner = re.search('@(?P<owner>\S+)\S*', self.soup.find('meta', property='og:description').get('content'))
        self._raw_title = match_owner.group('owner')
        if '님' in self._raw_title:
            self.title = self._raw_title.split('님')[0]
        else:
            self.title = self._raw_title

        if self.soup.find('meta', property='og:video') is None:
            self.images = [self.soup.find('meta', property='og:image').get('content')]
        else:
            self.images = [self.soup.find('meta', property='og:video').get('content')]


class TwitterPage(PageBot):  # 'twitter.com' in url
    def __init__(self, url):
        super(TwitterPage, self).__init__(url)

    def read_page(self):
        self._get_soup()
        self.title = self._raw_title.split(':')[0].replace('트위터의 ', '').replace(' 님', '')

        if self.soup.find('meta', property='og:video:url') is None:
            for img in self.soup.find_all('img'):
                img_src = img.get('src')
                if img_src is not None and img_src.startswith('https://pbs.twimg.com/media/'):
                    self.images.append(img_src + ':orig')
        else:
            self.images = [self.soup.find('meta', property='og:video:url').get('content')]


class TistoryPage(PageBot):
    def __init__(self, url):
        super(TistoryPage, self).__init__(url)

    def read_page(self):
        self._get_soup()
        self._raw_title = []
        for t in self.soup.find_all('title'):
            self._raw_title.append(str(t.string.encode('euc-kr', 'ignore').decode('euc-kr')).strip())
        self.title = ' - '.join(self._raw_title)

        img_tag_class_candidate = ['article', 'tt_article_useless_p_margin', 'tr-etr-content']
        for candidate in img_tag_class_candidate:
            img_tag = self.soup.find('div', class_=candidate)
            if img_tag is None:
                continue
            for img in img_tag.find_all('img'):
                img_src = img.get('src')
                self.images.append(img_src + '?original')


def process_page(url):
    if 'dcinside.com' in url:
        bot = DCInsdePage(url)
    elif 'blog.naver.com' in url:
        bot = NaverBlogPage(url)
    elif 'post.naver.com' in url:
        bot = NaverPostPage(url)
    elif 'entertain.naver.com' in url:
        bot = NaverNews(url)
    elif 'Instagram' in url:
        bot = InstagramPage(url)
    elif 'twitter.com' in url:
        bot = TwitterPage(url)
    else:
        bot = TistoryPage(url)

    try:
        bot.read_page()
        return bot.title, bot.url, list(set(bot.images))
    except:
        return None
