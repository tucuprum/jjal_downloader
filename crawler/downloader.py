import os
import re
import imghdr
import urllib.parse as urlparse
import requests
import time
import hashlib
from datetime import datetime
from PIL import Image
if __name__ == '__main__':
    from crawler.common import DESKTOP_UA
else:
    from .common import DESKTOP_UA
try:
    from misc.config import Config
    parameter = Config().value
except ImportError:
    Config = None
    parameter = {'Download': {'TimeOut': 10, 'DownloadBlock': 1024, 'GUIInterval': 0.1}}


class DownloadImage(object):
    def __init__(self, url, directory='', page_title='', folder_per_page=False):
        self.url = url
        # web connection
        self.session = None  # type: requests.session
        self.total_size = 0
        self.total_size_str = ''
        self.downloaded_size = 0
        self.download_speed = 0
        self.resp = None
        self.image_pixel = None
        # local file
        self.orig_name = ''
        self.extension = ''
        self.temp_path = ''
        self.final_path = ''
        if folder_per_page and len(page_title) > 0:
            self.file_dir = os.path.join(directory, self._refine_path(page_title))
            if not os.path.exists(self.file_dir):
                os.mkdir(self.file_dir)
        else:
            self.file_dir = directory

    @staticmethod
    def _refine_path(name):
        forbidden_names = '[<>:/\\|?*\"]|[\0-\31]'
        forbidden_string = ['COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
                            'CON', 'PRN', 'AUX', 'NUL']

        if name in forbidden_string:
            return name + '- 다운로드'
        elif bool(re.search(forbidden_names, name)):
            return re.sub(forbidden_names, '-', name)
        else:
            return name

    @staticmethod
    def _size_to_str(value):
        KB = 1024
        MB = KB * KB
        GB = MB * KB

        if value > GB:
            return '{:.1f} GB'.format(value/GB)
        elif value > MB:
            return '{:.1f} MB'.format(value/MB)
        elif value > KB:
            return '{:.1f} KB'.format(value/KB)
        else:
            return '{} B'.format(value)

    def _get_extension(self):
        image_type = imghdr.what(self.temp_path)
        if image_type is None:
            with open(self.temp_path, 'rb') as file:
                self.extension = '.jpg' if file.read(16).startswith(b'\xff\xd8\xff') else '.unknown'
        elif image_type == 'jpeg':
            self.extension = '.jpg'
        else:
            self.extension = '.' + image_type

    def _get_new_name(self):
        self._get_extension()
        refined_name = self._refine_path(self.orig_name)
        self.final_path = os.path.join(self.file_dir, refined_name + self.extension)

        # 중복 피하기
        index = 0
        while os.path.exists(self.final_path):
            index += 1
            suffix = '_dup_{}'.format(index)
            self.final_path = os.path.join(self.file_dir, refined_name + suffix + self.extension)

    def _get_extra_headers(self):
        self.session.headers['Referer'] = self.url

    def _get_response(self):
        self.session = requests.session()
        self.session.headers['Accept'] = 'Accept: image/png, image/svg+xml, image/jxr, image/*; q=0.8, */*; q=0.5'
        self.session.headers['Accept-Encoding'] = 'gzip, deflate'
        self.session.headers['Accept-Language'] = 'ko, en-US; q=0.7, en; q=0.3'
        self.session.headers['Connection'] = 'Keep-Alive'
        self.session.headers['User-Agent'] = DESKTOP_UA
        self._get_extra_headers()

        self.resp = self.session.get(self.url, timeout=parameter['Download']['TimeOut'], stream=True)

    def _get_orig_name(self):
        pass

    def _parse_response(self):
        self._get_orig_name()
        self.orig_name = os.path.splitext(self.orig_name)[0]  # remove extension info from the name

        # parse size
        try:
            self.total_size = int(self.resp.headers['Content-Length'])
            self.total_size_str = self._size_to_str(self.total_size)
        except KeyError:
            self.total_size = 0
            self.total_size_str = ''

    def _send_signal(self):
        pass

    def _download(self):
        update_interval = parameter['Download']['GUIInterval']
        section = 0
        start_time = time.time()
        name_hash = hashlib.md5()
        name_hash.update(self.url.encode())
        if not os.path.exists('temp'):
            os.mkdir('temp')
        self.temp_path = os.path.join('temp', name_hash.hexdigest())

        with open(self.temp_path, 'wb') as file:
            for buf in self.resp.iter_content(chunk_size=parameter['Download']['DownloadBlock']):
                file.write(buf)

                # Check download speed
                curr_time = time.time()
                self.downloaded_size += len(buf)
                section += len(buf)
                if curr_time > start_time + update_interval:
                    self.download_speed = self._size_to_str(section / (curr_time - start_time))
                    start_time = curr_time
                    section = 0

                self._send_signal()

        self._get_new_name()
        os.rename(self.temp_path, self.final_path)
        self.total_size = self.downloaded_size
        self.total_size_str = self._size_to_str(self.total_size)

    def _terminate(self):
        self.session = None
        with Image.open(self.final_path) as img:
            self.image_pixel = img.size
        if os.path.exists(self.temp_path):
            os.remove(self.temp_path)

    def process(self):
        try:
            self._get_response()
        except Exception:
            return 1
        try:
            self._parse_response()
        except Exception:
            return 2
        try:
            self._download()
        except Exception:
            return 3

        self._terminate()
        return self.final_path, self.total_size_str, self.image_pixel


class DCDownload(DownloadImage):
    def __init__(self, url, directory, page_title, folder_per_page):
        super(DCDownload, self).__init__(url, directory, page_title, folder_per_page)

    def _get_extra_headers(self):
        self.session.headers['Host'] = 'image.dcinside.com'
        self.session.headers['Origin'] = 'http://image.dcinside.com'
        self.session.headers['Referer'] = self.url.replace('viewimage', 'viewimagePop')
        self.session.headers['Upgrade-Insecure-Requests'] = '1'

    def _get_orig_name(self):
        def gall_euckr_file_name(raw_str):
            def alphabet_to_euckr(str1, str2):  # 'be', 'c6' => '아'
                return bytes([int('0x' + str1, 16), int('0x' + str2, 16)]).decode('euc-kr')

            binary = str(raw_str.encode('unicode_escape'))[2:-1].replace(r'\\\\', r'\\')
            # '\\xa5\\xbe\\xbe...  \\ is one char
            decoded_list = list()
            i = 0
            while True:
                if i >= len(binary):
                    break
                elif binary[i:i+2] == '\\x':
                    decoded = (alphabet_to_euckr(binary[i+2:i+4], binary[i+6:i+8]))
                    decoded_list.append(decoded)
                    i += 8
                else:
                    decoded_list.append(binary[i])
                    i += 1

            return ''.join(decoded_list)

        try:
            self.orig_name = gall_euckr_file_name(self.resp.headers['Content-Disposition'].split('filename=')[1]
                                                  .replace('"', ''))
        except:
            self.orig_name = datetime.now().strftime('%Y%m%d-%H%M%S')


class NaverpostDownload(DownloadImage):
    def __init__(self, url, directory, page_title, folder_per_page):
        super(NaverpostDownload, self).__init__(url, directory, page_title, folder_per_page)

    def _get_orig_name(self):
        self.orig_name = urlparse.unquote(self.url.split('/')[-1])


class TistoryDownload(DownloadImage):
    def __init__(self, url, directory, page_title, folder_per_page):
        super(TistoryDownload, self).__init__(url, directory, page_title, folder_per_page)

    def _get_orig_name(self):
        mat = re.search("filename\*=UTF-8''(?P<file>\S+)$", self.resp.headers['Content-Disposition'])
        if bool(mat):
            self.orig_name = urlparse.unquote(mat.group('file'))
        else:
            self.orig_name = datetime.now().strftime('%Y%m%d-%H%M%S')


def download_image(url, directory='', page_title='', folder_per_page=False):
    if 'dcinside.com' in url:
        bot = DCDownload(url, directory, page_title, folder_per_page)
    elif 'post-phinf.pstatic.net' in url:
        bot = NaverpostDownload(url, directory, page_title, folder_per_page)
    else:
        bot = TistoryDownload(url, directory, page_title, folder_per_page)

    ret = bot.process()
    return ret
