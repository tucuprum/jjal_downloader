import os
import hashlib
from datetime import datetime


def get_hash(file):
    hash_func = hashlib.md5()
    with open(file, 'rb') as f_point:
        for chunk in iter(lambda: f_point.read(8192), b''):
            hash_func.update(chunk)
    return hash_func.hexdigest()


class RemoveDuplicate(object):
    def __init__(self, target_dir, move_file=False, init_callback= None, proc_callback=None, term_callback=None):
        self.target_dir = target_dir
        self.file_list = []
        self.dup_dict = {}
        self.hash_dict = {}
        self.log = os.path.join(self.target_dir, '중복결과_{}.txt'.format(datetime.now().strftime('%Y%m%d-%H%M%S')))
        self.move_file = move_file
        self.init_callback = init_callback
        self.proc_callback = proc_callback
        self.term_callback = term_callback

    def _list_all(self):
        for directory, subfolders, files in os.walk(self.target_dir):
            for file_name in files:
                self.file_list.append(os.path.join(directory, file_name))

    def _check_duplicate_exist(self, file):
        hash_value = get_hash(file)
        if hash_value in self.hash_dict:  # 중복이 있으면 파일은 제거하고 원본 파일 리턴
            self.file_list.remove(file)
            return self.hash_dict[hash_value]
        else:  # 중복이 없으면 해시 등록하고 None 리턴
            self.hash_dict[hash_value] = file
            return None

    def _move_duplicate(self, file):
        duplicate_folder = os.path.join(self.target_dir, '[중복된 짤]')
        if not os.path.exists(duplicate_folder):
            os.mkdir(duplicate_folder)

        original_directory, original_file = os.path.split(file)
        original_filebase, original_ext = os.path.splitext(original_file)

        new_path = os.path.join(duplicate_folder, original_file)
        i = 0
        while os.path.exists(new_path):
            i += 1
            suffix = '_dup_{}'.format(i)
            new_path = os.path.join(duplicate_folder, original_filebase + suffix + original_ext)
        os.rename(file, new_path)

    def _generate_report(self):
        ret = []
        for index, (file, dup_list) in enumerate(self.dup_dict.items()):
            ret.append('{}. {}\n중복: {}\n---\n\n'.format(index+1, file, '\n'.join(dup_list)))
        with open(self.log, 'w') as f:
            f.write(''.join(ret))

    def process_one(self, file):
        if file in self.file_list:
            return None
        else:
            ret = self._check_duplicate_exist(file)
            if ret is not None:
                if ret in self.dup_dict:
                    self.dup_dict[ret].append(file)
                else:
                    self.dup_dict[ret] = [file]

    def _show_result(self):
        self._generate_report()
        os.startfile(self.log)

    def process(self):
        self._list_all()
        if self.init_callback is not None:
            self.init_callback.emit(len(self.file_list))

        for index, file in enumerate(self.file_list):

            if self.proc_callback is not None:
                self.proc_callback.emit([index, file])

            ret = self._check_duplicate_exist(file)
            if ret is None:
                continue
            elif ret in self.dup_dict:
                self.dup_dict[ret].append(file)
            else:
                self.dup_dict[ret] = [file]

        if self.term_callback is not None:
            self.term_callback.emit(True)

        self._show_result()
        if self.move_file:
            for _, dup_list in self.dup_dict.items():
                for file in dup_list:
                    self._move_duplicate(file)
