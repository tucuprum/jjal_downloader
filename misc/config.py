import os
from configparser import ConfigParser


class Config(object):
    FILE_PATH = 'config.ini'
    DEFAULT_VALUE = {'Download': {'FolderPerPage': False, 'DestinationDirectory': '', 'TimeOut': 10,
                                  'DownloadBlock': 1024, 'GUIInterval': 0.1, 'Thread': 2},
                     'Filter': {'Parser': ',', 'Keyword': ''}}

    def __init__(self):
        self.config = ConfigParser()
        self.config.read_dict(self.DEFAULT_VALUE)
        self.value = self.DEFAULT_VALUE
        self.load_file_or_reset()
        self.config_to_dict()

    def _save_config(self):
        with open(self.FILE_PATH, 'w', encoding='UTF-8') as fp:
            self.config.write(fp)

    def load_file_or_reset(self):
        if os.path.exists(self.FILE_PATH):
            self.config.read_file(open(self.FILE_PATH, 'r', encoding='UTF-8'))

        self._save_config()

    def save_value(self):
        self._dict_to_config()
        self._save_config()

    def _dict_to_config(self):
        self.config.read_dict(self.value)

    def config_to_dict(self):
        for section in self.DEFAULT_VALUE.keys():
            for option in self.DEFAULT_VALUE[section].keys():
                ret = None
                try:
                    if option == 'FolderPerPage':
                        ret = self.config.getboolean(section, option)
                    elif option in ['DownloadBlock', 'TimeOut']:
                        ret = self.config.getint(section, option)
                    elif option == 'GUIInterval':
                        ret = self.config.getfloat(section, option)
                    elif option == 'Thread':
                        ret = self.config.getint(section, option)
                    else:
                        ret = self.config.get(section, option)
                except ValueError:
                    ret = self.DEFAULT_VALUE[section][option]
                    self.value[section][option] = ret
                    self.config.set(section, option, str(ret))
                    self._save_config()
                finally:
                    self.value[section][option] = ret


config = Config()
