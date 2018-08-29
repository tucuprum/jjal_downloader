import json
import threading
import queue
import os
import webbrowser
from os.path import expanduser
from PyQt5.QtGui import QPixmap, QPainter, QColor, QBrush
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QMutex, QObject, Qt
from PyQt5.QtWidgets import (QDialog, QWizard, QMainWindow, QMessageBox, QFileDialog, QInputDialog,
                             QDialogButtonBox, QListWidgetItem, QTreeWidgetItem, QGraphicsScene, QGraphicsPixmapItem)
from crawler.list_analyze import find_gall, DCInsideList, TistoryList, ListBot
from crawler.page_analyze import process_page
from crawler.downloader import download_image
from gui import _manual_add, _auto_add, _option_window, _main_window, _popup_message, _duplicate, _info, _gall_search
from misc.config import config
from misc.remove_duplicate import RemoveDuplicate

NUMBER_OF_THREAD = config.value['Download']['Thread']
threadLimiter = threading.BoundedSemaphore(NUMBER_OF_THREAD)


def define_thread_num(value):
    global NUMBER_OF_THREAD
    global threadLimiter

    NUMBER_OF_THREAD = value
    threadLimiter = threading.BoundedSemaphore(value)


def display_error(parent, message, detail=None, critical=False):
    msg = QMessageBox(parent)
    if critical:
        msg.setIcon(QMessageBox.Critical)
    else:
        msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle('짤 다운로더')
    msg.setText(message)
    if detail is not None:
        msg.setDetailedText(str(detail))
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec()


def display_info(parent, message, detail=None):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle('짤 다운로더')
    msg.setText(message)
    if detail is not None:
        msg.setDetailedText(str(detail))
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec()


def ask_yes_no(message, parent=None):
    popup = QDialog(parent)
    popup.ui = _popup_message.Ui_Dialog()
    popup.ui.setupUi(popup)
    popup.ui.label.setText(message)

    return popup.exec_()


class DuplicateThread(QThread):
    def __init__(self, target_folder, move_file, init_callback, process_callback, terminate_callback):
        super(DuplicateThread, self).__init__()
        self.work = True
        self.mutex = QMutex()
        self.dup_bot = RemoveDuplicate(target_folder, move_file=move_file, init_callback=init_callback,
                                       proc_callback=process_callback, term_callback=terminate_callback)

    def __del__(self):
        self.wait()

    def run(self):
        if not self.work:
            return None

        self.mutex.lock()
        self.dup_bot.process()
        self.mutex.unlock()


class PageAnalyzeThread(QThread):
    process_result = pyqtSignal(object)
    terminal = pyqtSignal(bool)

    def __init__(self, page_range):
        super(PageAnalyzeThread, self).__init__()
        self.page_range = page_range
        self.work = True
        self.mutex = QMutex()

    def __del__(self):
        self.wait()

    def on_changed_value(self, index, result):
        ret = [index] + list(result)
        self.process_result.emit(ret)  # index, page_title, page_url, page_images

    def on_termination(self):
        self.terminal.emit(True)

    def stop(self):
        self.mutex.lock()
        self.work = False
        self.mutex.unlock()
        self.on_termination()

    def run(self):
        for index, page in enumerate(self.page_range):
            if not self.work:
                break

            self.mutex.lock()
            ret = process_page(page)
            if ret is not None:
                self.on_changed_value(index + 1, ret)
            self.mutex.unlock()

        self.on_termination()


class ThreadCounter(QObject):
    completed = pyqtSignal()


class ImageDownloadSignal(QObject):
    output_signal = pyqtSignal(object)
    onset_signal = pyqtSignal(object)


class ImageDownloadThread(threading.Thread):
    def __init__(self, image_url, site_name, upper_index, lower_index, counter, event):
        super(ImageDownloadThread, self).__init__()
        self.image_url = image_url
        self.site_name = site_name
        self.upper_index = upper_index
        self.lower_index = lower_index
        self.counter = counter
        self.signal = ImageDownloadSignal()
        self.event = event

    def run(self):
        threadLimiter.acquire()
        if self.event.is_set():
            threadLimiter.release()
            return None

        self.signal.onset_signal.emit([self.upper_index, self.lower_index])
        ret = download_image(self.image_url, page_title=self.site_name,
                             directory=config.value['Download']['DestinationDirectory'],
                             folder_per_page=config.value['Download']['FolderPerPage'])
        self.signal.output_signal.emit([ret, self.upper_index, self.lower_index])
        self.counter.completed.emit()
        threadLimiter.release()

    def stop(self):
        self.event.set()


class DuplicateWindow(QWizard):
    initial_callback = pyqtSignal(int)
    process_callback = pyqtSignal(object)
    terminate_callback = pyqtSignal(bool)

    def __init__(self, parent=None):
        super(DuplicateWindow, self).__init__(parent=parent)
        self.ui = _duplicate.Ui_Wizard()
        self.ui.setupUi(self)
        self.flow()
        self.target_files = []
        self.dup_thread = None

    def directory_finder(self):
        ret = QFileDialog.getExistingDirectory(self, '폴더를 선택해주세요', expanduser('~'),
                                               QFileDialog.ShowDirsOnly)
        self.ui.lineEdit.setText(str(ret))

    def flow(self):
        def intro_flow():
            target_dir = self.ui.lineEdit.text().strip()
            if len(target_dir) == 0:
                return 0

            elif not os.path.exists(target_dir):
                display_error(self, '해당 폴더가 존재하지 않습니다. 입력이 정확한지 확인해주세요.')
                return 0

            elif not os.path.isdir(target_dir):
                display_error(self, '해당 경로가 폴더가 맞는지 확인해주세요.')
                return 0

            else:
                move_file = self.ui.checkBox.isChecked()
                self.dup_thread = DuplicateThread(target_dir, move_file, self.initial_callback, self.process_callback,
                                                  self.terminate_callback)
                return 1

        def process_config():
            @pyqtSlot(int)
            def progress_bar_initialize(value):
                self.ui.progressBar.setMaximum(value)
                self.ui.progressBar.setValue(0)

            @pyqtSlot(object)
            def progress_bar_update(ret):  # file_path
                index, file = ret
                self.ui.progressBar.setValue(index)
                if len(file) > 40:
                    file = file[:15] + ' ... ' + file[-15:]
                self.ui.processing_page.setText('처리 중인 파일: ' + file)

            @pyqtSlot(bool)
            def process_term(value):
                if value:
                    self.ui.process.isComplete = lambda: True
                    self.ui.process.completeChanged.emit()

            @pyqtSlot()
            def go_to_final_page():
                self.next()

            # def ask_terminate():
            #     self.auto_worker.mutex.lock()
            #     ret = ask_yes_no('아직 작업이 종료되지 않았습니다. 종료하시겠습니까?', self)
            #     self.auto_worker.mutex.unlock()
            #     if ret:
            #         self.auto_worker.stop()
            #
            #     return ret
            #
            # def cancel():
            #     if ask_terminate():
            #         self.reject()
            #
            # def goback():
            #     if ask_terminate():
            #         self.back()

            # self.button(QWizard.CancelButton).disconnect()
            # self.button(QWizard.CancelButton).clicked.connect(cancel)
            self.button(QWizard.BackButton).disconnect()
            self.button(QWizard.BackButton).clicked.connect(lambda: None)
            self.button(QWizard.CancelButton).setDisabled(True)
            # self.button(QWizard.BackButton).setDisabled(True)
            self.ui.process.completeChanged.connect(go_to_final_page)

            self.initial_callback.connect(progress_bar_initialize)
            self.process_callback.connect(progress_bar_update)
            self.terminate_callback.connect(process_term)
            self.dup_thread.start()

        self.setButtonText(QWizard.NextButton, '다음')
        self.setButtonText(QWizard.FinishButton, '종료')
        self.setButtonText(QWizard.CancelButton, '취소')

        self.ui.pushButton.clicked.connect(self.directory_finder)

        self.ui.intro.nextId = intro_flow
        self.ui.process.isCommitPage = lambda: True
        self.ui.process.isComplete = lambda: False
        self.ui.process.initializePage = process_config
        self.ui.concl.isCommitPage = lambda: True


class ManualAddWindow(QWizard):
    def __init__(self, parent=None):
        super(ManualAddWindow, self).__init__(parent=parent)
        self.ui = _manual_add.Ui_Wizard()
        self.ui.setupUi(self)
        self.flow()
        self.input_pages = []
        self.auto_worker = None  # type: PageAnalyzeThread

    def flow(self):
        def intro_flow():
            user_input = self.ui.manual_input.toPlainText().strip()
            if len(user_input) == 0:
                return 0

            else:
                try:
                    self.input_pages = user_input.split('\n')
                except Exception as e:
                    display_error(self, '입력한 범위 분석 중에 오류가 발생했습니다. 입력이 정확한지 확인해주세요.', detail=e)
                    return 0
                return 1

        def process_config():
            @pyqtSlot(object)
            def progress_bar_update(value):  # index, page_title, page_url, page_images
                self.ui.progressBar.setValue(value[0])
                self.ui.processing_page.setText('처리 중인 페이지: ' + value[1])
                self.parent().add_item(value)

            @pyqtSlot(bool)
            def process_term(value):
                if value:
                    self.ui.process.isComplete = lambda: True
                    self.ui.process.completeChanged.emit()

            @pyqtSlot()
            def go_to_final_page():
                self.next()

            def ask_terminate():
                self.auto_worker.mutex.lock()
                ret = ask_yes_no('아직 작업이 종료되지 않았습니다. 종료하시겠습니까?', self)
                self.auto_worker.mutex.unlock()
                if ret:
                    self.auto_worker.stop()

                return ret

            def cancel():
                if ask_terminate():
                    self.reject()

            def goback():
                if ask_terminate():
                    self.back()

            self.ui.progressBar.setMaximum(len(self.input_pages))
            self.ui.progressBar.setValue(0)
            self.worker = PageAnalyzeThread(self.input_pages)
            self.button(QWizard.CancelButton).disconnect()
            self.button(QWizard.CancelButton).clicked.connect(cancel)
            self.button(QWizard.BackButton).disconnect()
            self.button(QWizard.BackButton).clicked.connect(goback)
            self.ui.process.completeChanged.connect(go_to_final_page)

            self.auto_worker = PageAnalyzeThread(self.input_pages)
            self.auto_worker.process_result.connect(progress_bar_update)
            self.auto_worker.terminal.connect(process_term)
            self.auto_worker.start()

        self.setButtonText(QWizard.NextButton, '다음')
        self.setButtonText(QWizard.FinishButton, '종료')
        self.setButtonText(QWizard.CancelButton, '취소')

        self.ui.intro.nextId = intro_flow
        self.ui.process.isComplete = lambda: False
        self.ui.process.initializePage = process_config
        self.ui.concl.isCommitPage = lambda: True


class GallSearchPopup(QDialog):
    def __init__(self, parent=None):
        super(GallSearchPopup, self).__init__(parent=parent)
        self.ui = _gall_search.Ui_Dialog()
        self.ui.setupUi(self)
        self.user_input = ''
        self.candidates = []
        self.ret = None
        self.target = None
        self.config()

    def config(self):
        self.ui.pushButton.clicked.connect(self.process_input)
        self.ui.buttonBox.clicked.connect(self.button_box_connect)
        # self.ui.listView.clicked.connect(self.update_target)

        self.ui.buttonBox.button(QDialogButtonBox.Ok).setText('확인')
        self.ui.buttonBox.button(QDialogButtonBox.Cancel).setText('취소')

    def process_input(self):
        self.user_input = self.ui.lineEdit.text().strip()
        if len(self.user_input) == 0:
            return None

        try:
            self.candidates = find_gall(self.user_input)
        except Exception as e:
            display_error(self, '검색 도중에 오류가 발생했습니다. 키워드를 다시 입력해주세요.', detail=e)

        if len(self.candidates) == 0:
            display_error(self, '검색 결과가 없습니다. 키워드를 다시 입력해주세요.')
            return None

        self.ui.listWidget.clear()
        for name, _ in self.candidates:
            item = QListWidgetItem(name, parent=self.ui.listWidget)
            self.ui.listWidget.addItem(item)

    def button_box_connect(self, button):
        target_btn = self.ui.buttonBox.standardButton(button)
        if target_btn == QDialogButtonBox.Ok:
            selected = self.ui.listWidget.selectedIndexes()
            if len(selected) == 0:
                return None
            else:
                self.ret = self.candidates[selected[0].row()]

        elif target_btn == QDialogButtonBox.Cancel:
            self.close()
        else:
            return None


class AutoAddWindow(QWizard):
    def __init__(self, parent=None):
        super(AutoAddWindow, self).__init__(parent=parent)
        self.ui = _auto_add.Ui_Wizard()
        self.ui.setupUi(self)
        self.connect()
        self.flow()
        self.list_bot = None  # type: ListBot
        self.list_bot_result = None
        self.auto_worker = None  # type: PageAnalyzeThread

    def connect(self):
        self.ui.gall1_search.clicked.connect(self.open_popup)

    def open_popup(self):
        window = GallSearchPopup()
        if window.exec_():
            self.ui.gall1_input.setText(window.ret[1])

    def flow(self):
        def intro_flow():
            if self.ui.radioButton_gall.isChecked():
                return 2
            elif self.ui.radioButton_tistory.isChecked():
                return 1
            else:
                return 0

        def tistory1_flow():
            user_input = self.ui.tistory1_input.text().strip()
            if len(user_input) == 0:
                return 0
            else:
                try:
                    self.list_bot = TistoryList(user_input)
                    self.list_bot.get_last_list()
                except Exception as e:
                    self.list_bot = None
                    display_error(self, '사이트 분석 중에 오류가 발생했습니다. 입력이 정확한지 확인해주세요.', detail=e)
                    return 0
                self.ui.tistory2_info.setText('선택한 사이트: {}\n\n선택 가능한 범주: 1-{} (클수록 최신)\n\n'
                                              .format(self.list_bot.title, self.list_bot.last_list))
                return 3

        def tistory2_flow():
            user_input = self.ui.tistory2_input.text().strip()
            if len(user_input) == 0:
                return 0
            else:
                try:
                    self.list_bot_result = self.list_bot.get_target_pages(user_input)
                except Exception as e:
                    display_error(self, '입력한 범위 분석 중에 오류가 발생했습니다. 입력이 정확한지 확인해주세요.', detail=e)
                    return 0
                self.ui.progressBar.setRange(0, len(self.list_bot_result))
                return 5

        def gall1_flow():
            user_input = self.ui.gall1_input.text().strip()
            if len(user_input) == 0:
                return 0
            else:
                try:
                    self.list_bot = DCInsideList(code=user_input,
                                                 recommend=self.ui.gall1_rec.isChecked(),
                                                 keyword_filter=self.ui.gall1_filter.isChecked())
                    self.list_bot.get_last_list()
                except Exception as e:
                    self.list_bot = None
                    display_error(self, '갤러리 분석 중에 오류가 발생했습니다. 입력이 정확한지 확인해주세요.', detail=e)
                    return 0
                self.ui.gall2_info.setText('선택한 갤러리: {}\n\n선택 가능한 범주: 1-{} (작을수록 최신)\n\n'
                                           .format(self.list_bot.title, self.list_bot.last_list))

                return 4

        def gall2_flow():
            user_input = self.ui.gall2_input.text().strip()
            if len(user_input) == 0:
                return 0
            else:
                try:
                    self.list_bot_result = self.list_bot.get_target_pages(user_input)
                except Exception as e:
                    display_error(self, '입력한 범위 분석 중에 오류가 발생했습니다. 입력이 정확한지 확인해주세요.', detail=e)
                    return 0
                return 5

        def process_config():
            @pyqtSlot(object)
            def progress_bar_update(value):  # index, page_title, page_url, page_images
                self.ui.progressBar.setValue(value[0])
                self.ui.processing_page.setText('처리 중인 페이지: ' + value[1])
                self.parent().add_item(value)

            @pyqtSlot(bool)
            def process_term(value):
                if value:
                    self.ui.process.isComplete = lambda: True
                    self.ui.process.completeChanged.emit()

            @pyqtSlot()
            def go_to_final_page():
                self.next()

            def ask_terminate():
                self.auto_worker.mutex.lock()
                ret = ask_yes_no('아직 작업이 종료되지 않았습니다. 종료하시겠습니까?', self)
                self.auto_worker.mutex.unlock()
                if ret:
                    self.auto_worker.stop()

                return ret

            def cancel():
                if ask_terminate():
                    self.reject()

            def goback():
                if ask_terminate():
                    self.back()

            self.ui.progressBar.setMaximum(len(self.list_bot_result))
            self.ui.progressBar.setValue(0)
            self.button(QWizard.CancelButton).disconnect()
            self.button(QWizard.CancelButton).clicked.connect(cancel)
            self.button(QWizard.BackButton).disconnect()
            self.button(QWizard.BackButton).clicked.connect(goback)
            self.ui.process.completeChanged.connect(go_to_final_page)

            self.auto_worker = PageAnalyzeThread(self.list_bot_result)
            self.auto_worker.process_result.connect(progress_bar_update)
            self.auto_worker.terminal.connect(process_term)
            self.auto_worker.start()

        self.setButtonText(QWizard.NextButton, '다음')
        self.setButtonText(QWizard.FinishButton, '종료')
        self.setButtonText(QWizard.CancelButton, '취소')

        self.ui.intro.nextId = intro_flow
        self.ui.tistory1.nextId = tistory1_flow
        self.ui.gall1.nextId = gall1_flow
        self.ui.tistory2.nextId = tistory2_flow
        self.ui.gall2.nextId = gall2_flow
        self.ui.process.nextId = lambda: 6
        self.ui.process.isComplete = lambda: False
        self.ui.process.initializePage = process_config
        self.ui.concl.isCommitPage = lambda: True


class OptionWindow(QDialog):
    def __init__(self, parent=None):
        super(OptionWindow, self).__init__(parent=parent)
        self.ui = _option_window.Ui_Dialog()
        self.ui.setupUi(self)
        self.connect()
        self._read_config()

    def _read_config(self):
        self.ui.gui_interval.setValue(config.value['Download']['GUIInterval'])
        self.ui.timeout.setValue(config.value['Download']['TimeOut'])
        self.ui.down_block.setValue(config.value['Download']['DownloadBlock'])
        self.ui.dir_per_page.setChecked(config.value['Download']['FolderPerPage'])
        define_thread_num(config.value['Download']['Thread'])
        self.ui.destFolderEdit.clear()
        self.ui.destFolderEdit.insert(config.value['Download']['DestinationDirectory'])
        if len(config.value['Filter']['Keyword']) > 0:
            self.ui.filter_list.addItems(config.value['Filter']['Keyword'].split(config.value['Filter']['Parser']))

    def _save_config(self):
        parser = config.value['Filter']['Parser']
        config.value['Download']['GUIInterval'] = self.ui.gui_interval.value()
        config.value['Download']['FolderPerPage'] = self.ui.dir_per_page.isChecked()
        config.value['Download']['DownloadBlock'] = self.ui.down_block.value()
        config.value['Download']['Thread'] = self.ui.threadnum.value()
        config.value['Download']['DestinationDirectory'] = self.ui.destFolderEdit.text()
        config.value['Filter']['Keyword'] = parser.join([self.ui.filter_list.item(i).text()
                                                         for i in range(self.ui.filter_list.count())])
        config.save_value()

    def connect(self):
        def directory_finder():
            ret = QFileDialog.getExistingDirectory(self, '폴더를 선택해주세요', expanduser('~'),
                                                   QFileDialog.ShowDirsOnly)
            self.ui.destFolderEdit.setText(str(ret))

        def get_single_keyword():
            text, confirm = QInputDialog.getText(self, '키워드 입력', '필터할 키워드를 입력해주세요: ')
            if confirm:
                self.ui.filter_list.addItem(text.strip())

        def delete_single_keyword():
            for item in self.ui.filter_list.selectedItems():
                self.ui.filter_list.takeItem(self.ui.filter_list.row(item))

        def delete_all_keyword():
            if self.ui.filter_list.count() == 0:
                return None
            if ask_yes_no('정말로 모든 키워드를 지우시겠습니까?', self):
                [self.ui.filter_list.takeItem(i) for i in range(self.ui.filter_list.count())]

        def button_box_connect(button):
            target_btn = self.ui.buttonBox.standardButton(button)
            if target_btn == QDialogButtonBox.Apply:
                self._save_config()
            elif target_btn == QDialogButtonBox.Ok:
                self._save_config()
                self.close()
            elif target_btn == QDialogButtonBox.Cancel:
                self.close()
            elif target_btn == QDialogButtonBox.RestoreDefaults:
                if ask_yes_no('정말로 모든 세팅을 초기화하시겠습니까?', self):
                    config.value = config.DEFAULT_VALUE
                    self._read_config()
            else:
                return None

        self.ui.buttonBox.button(QDialogButtonBox.Ok).setText('확인')
        self.ui.buttonBox.button(QDialogButtonBox.Apply).setText('적용')
        self.ui.buttonBox.button(QDialogButtonBox.Cancel).setText('취소')
        self.ui.buttonBox.button(QDialogButtonBox.RestoreDefaults).setText('초기화')

        self.ui.findFolderBtn.clicked.connect(directory_finder)
        self.ui.filter_add.clicked.connect(get_single_keyword)
        self.ui.filter_substract.clicked.connect(delete_single_keyword)
        self.ui.filter_reset.clicked.connect(delete_all_keyword)
        self.ui.buttonBox.clicked.connect(button_box_connect)


class InfoWindow(QDialog):
    def __init__(self, parent=None):
        super(InfoWindow, self).__init__(parent=parent)
        self.ui = _info.Ui_Dialog()
        self.ui.setupUi(self)
        self.config()

    def config(self):
        self.resize(500, 300)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent=parent)
        self.ui = _main_window.Ui_mainWindow()
        self.ui.setupUi(self)
        self.connect()
        self.adjust_detail()

        self.threads = []
        self.counter_threads = 0
        self.total_num = 0
        self.success_num = 0
        self.fail_num = 0
        self.done_num = 0
        self.queue = queue.Queue()
        self.mutex = QMutex()
        self.event = threading.Event()
        self.scene = QGraphicsScene()

    def connect(self):
        self.ui.actionload_list.triggered.connect(self.import_tree)
        self.ui.actionsave_list.triggered.connect(self.export_tree)
        self.ui.actionduplicate.triggered.connect(self.open_duplicate)
        self.ui.actionclassifier_link.triggered.connect(self.open_classifier)
        self.ui.actionhelp.triggered.connect(self.open_help)
        self.ui.actioninfo.triggered.connect(self.open_info)

        self.ui.manualAddButton.clicked.connect(self.manual_clicked)
        self.ui.autoAddButton.clicked.connect(self.auto_clicked)
        self.ui.settingButton.clicked.connect(self.setting_clicked)
        self.ui.deleteButton.clicked.connect(self.delete_item)
        self.ui.cleanButton.clicked.connect(self.clean_item)
        self.ui.executeButton.clicked.connect(self.download_items)
        self.ui.loadButton.clicked.connect(self.import_tree)
        self.ui.saveButton.clicked.connect(self.export_tree)
        self.ui.folderButton.clicked.connect(self.open_folder)
        self.ui.treeWidget.itemClicked.connect(self.image_viewer)
        self.ui.treeWidget.itemDoubleClicked.connect(self.image_open)

    def adjust_detail(self):
        self.ui.treeWidget.setColumnWidth(0, 150)
        self.ui.treeWidget.setColumnWidth(1, 220)

    @staticmethod
    def open_classifier():
        webbrowser.open('http://gall.dcinside.com/board/view/?id=lovelyz&no=4117951')

    @staticmethod
    def open_help():
        webbrowser.open('http://gall.dcinside.com/board/view/?id=lovelyz&no=4778642')

    def open_info(self):
        window = InfoWindow(self)
        window.exec_()

    @staticmethod
    def open_folder():
        os.startfile(config.value['Download']['DestinationDirectory'])

    def open_duplicate(self):
        window = DuplicateWindow(self)
        window.exec_()

    def manual_clicked(self):
        window = ManualAddWindow(self)
        window.exec_()

    def auto_clicked(self):
        window = AutoAddWindow(self)
        window.exec_()

    def setting_clicked(self):
        window = OptionWindow(self)
        window.exec_()

    def export_tree(self):
        ans, _ = QFileDialog.getSaveFileName(self, '파일을 선택해주세요', expanduser('~'), "짤 다운로더 파일 (*.jdf)")
        if ans:
            ret = []
            header_list = self.ui.treeWidget.headerItem()
            for page_index in range(self.ui.treeWidget.topLevelItemCount()):
                page_item = self.ui.treeWidget.topLevelItem(page_index)
                page_data = {header_list.text(i): page_item.text(i) for i in range(header_list.columnCount())}
                images = []
                for image_index in range(page_item.childCount()):
                    image_item = page_item.child(image_index)
                    image_data = {header_list.text(i): image_item.text(i) for i in range(header_list.columnCount())}
                    images.append(image_data)
                page_data['image'] = images
                ret.append(page_data)

            with open(ans, 'w', encoding='utf-8') as fp:
                json.dump(ret, fp)

    def import_tree(self):
        ret, _ = QFileDialog.getOpenFileName(self, '파일을 선택해주세요', expanduser('~'), "짤 다운로더 파일 (*.jdf)")
        if ret:
            with open(ret, 'r', encoding='utf-8') as fp:
                loaded = json.load(fp)

            for page in loaded:
                try:
                    ret = [None, page['제목'], page['주소'], [image['주소'] for image in page['image']]]
                    self.add_item(ret)
                except Exception as e:
                    display_error(self, '파일을 읽어오는 중에 오류가 발생했습니다.', detail=e)
                    continue

    def add_item(self, value):
        _, page_title, page_url, page_images = value
        upper_item = QTreeWidgetItem(self.ui.treeWidget, [page_url, page_title])
        self.ui.treeWidget.addTopLevelItem(upper_item)

        for image in page_images:
            lower_item = QTreeWidgetItem(upper_item, [image])
            upper_item.addChild(lower_item)

        self.ui.treeWidget.expandToDepth(0)

    def delete_item(self):
        root = self.ui.treeWidget.invisibleRootItem()
        for selected in self.ui.treeWidget.selectedItems():
            (root or selected.parent()).removeChild(selected)

    def clean_item(self):
        root = self.ui.treeWidget.invisibleRootItem()
        target_upper = []
        for upper_index in range(self.ui.treeWidget.topLevelItemCount()):
            upper_item = self.ui.treeWidget.topLevelItem(upper_index)
            target_lower = []
            for lower_index in range(upper_item.childCount()):
                lower_item = upper_item.child(lower_index)
                if lower_item.text(3) == '다운로드 완료':
                    target_lower.append(lower_item)

            [upper_item.removeChild(item) for item in target_lower]
            if upper_item.childCount() == 0:
                target_upper.append(upper_item)

        [root.removeChild(item) for item in target_upper]

        display_info(self, '다운로드 완료한 내역을 목록에서 정리하였습니다.')

    def in_donwload_disable(self):
        self.ui.manualAddButton.setDisabled(True)
        self.ui.autoAddButton.setDisabled(True)
        self.ui.settingButton.setDisabled(True)
        self.ui.deleteButton.setDisabled(True)
        self.ui.cleanButton.setDisabled(True)
        self.ui.executeButton.clicked.disconnect(self.download_items)
        self.ui.executeButton.clicked.connect(self.stop_donwload)
        self.ui.executeButton.setChecked(True)

    def end_donwload_enable(self):
        self.ui.manualAddButton.setDisabled(False)
        self.ui.autoAddButton.setDisabled(False)
        self.ui.settingButton.setDisabled(False)
        self.ui.deleteButton.setDisabled(False)
        self.ui.cleanButton.setDisabled(False)
        self.ui.executeButton.clicked.disconnect(self.stop_donwload)
        self.ui.executeButton.clicked.connect(self.download_items)
        self.ui.executeButton.setChecked(False)

        for i in range(NUMBER_OF_THREAD):
            self.queue.put(None)
        for t in self.threads:
            t.join()
        for file in os.listdir('temp'):
            os.remove(os.path.join('temp', file))

        self.event.clear()
        self.in_donwload_status_bar()
        display_info(self, '다운로드 모두 완료')

    def reset_status_bar(self):
        self.mutex.lock()
        self.total_num = 0
        self.done_num = 0
        self.success_num = 0
        self.fail_num = 0
        self.mutex.unlock()

    def in_donwload_status_bar(self):
        self.mutex.lock()
        self.total_num = len(self.threads)
        self.done_num = self.success_num + self.fail_num
        message = ('작업 상태: 총 {}개 중 {}개 완료 ({}개 성공, {}개 실패)'
                   ).format(self.total_num, self.done_num, self.success_num, self.fail_num)
        self.ui.statusbar.showMessage(message)
        self.mutex.unlock()

    @staticmethod
    def reset_background(item):
        brush = QBrush(QColor('white'))
        for i in range(4):
            item.setBackground(i, brush)

    @staticmethod
    def set_warning_background(item):
        brush = QBrush(QColor('yellow'))
        for i in range(4):
            item.setBackground(i, brush)

    @pyqtSlot(object)
    def download_start_update(self, arg):
        upper_index, lower_index = arg
        upper_item = self.ui.treeWidget.topLevelItem(upper_index)
        lower_item = upper_item.child(lower_index)
        lower_item.setText(3, '다운로드 중')
        self.in_donwload_status_bar()

    @pyqtSlot(object)
    def download_done_update(self, arg):
        ret, upper_index, lower_index = arg
        upper_item = self.ui.treeWidget.topLevelItem(upper_index)
        lower_item = upper_item.child(lower_index)

        if ret == 0:
            lower_item.setText(3, '다운로드 실패: 프로그램 오류')
            self.set_warning_background(lower_item)
            self.fail_num += 1
        elif ret == 1:
            lower_item.setText(3, '다운로드 실패: 서버 접속 오류')
            self.set_warning_background(lower_item)
            self.fail_num += 1
        elif ret == 2:
            lower_item.setText(3, '다운로드 실패: 통신 분석 오류')
            self.set_warning_background(lower_item)
            self.fail_num += 1
        elif ret == 3:
            lower_item.setText(3, '다운로드 실패: 다운로드 오류')
            self.set_warning_background(lower_item)
            self.fail_num += 1
        else:
            file_path, file_size, image_size = ret
            lower_item.setText(1, file_path)
            lower_item.setText(2, '{} ({}x{})'.format(file_size, image_size[0], image_size[1]))
            lower_item.setText(3, '다운로드 완료')
            self.reset_background(lower_item)
            self.success_num += 1

        self.in_donwload_status_bar()

    @pyqtSlot()
    def stop_donwload(self):
        ret = ask_yes_no('진행 중인 다운로드를 멈추시겠습니까?', self)
        if ret:
            self.event.set()
            self.end_donwload_enable()

    @pyqtSlot()
    def download_complete(self):
        self.mutex.lock()
        self.counter_threads -= 1
        self.mutex.unlock()
        if self.counter_threads == 0:
            self.end_donwload_enable()

    def download_items(self):
        self.reset_status_bar()
        self.in_donwload_disable()
        self.threads = []
        self.counter_threads = 0
        counter = ThreadCounter()
        for upper_index in range(self.ui.treeWidget.topLevelItemCount()):
            upper_item = self.ui.treeWidget.topLevelItem(upper_index)
            site_name = upper_item.text(1)
            for lower_index in range(upper_item.childCount()):
                lower_item = upper_item.child(lower_index)
                image_url = lower_item.text(0)

                thread = ImageDownloadThread(image_url, site_name, upper_index, lower_index, counter, self.event)
                thread.signal.onset_signal.connect(self.download_start_update)
                thread.signal.output_signal.connect(self.download_done_update)
                self.threads.append(thread)
                self.queue.put(thread)
                self.mutex.lock()
                self.counter_threads += 1
                self.mutex.unlock()

                thread.start()

        counter.completed.connect(self.download_complete)

    def render_image(self, file):
        self.scene.clear()
        pixel_map = QPixmap(file)
        pixel_item = QGraphicsPixmapItem(pixel_map)
        self.scene.addItem(pixel_item)
        self.ui.graphicsView.setScene(self.scene)
        self.ui.graphicsView.setRenderHint(QPainter.Antialiasing)
        self.ui.graphicsView.fitInView(pixel_item, Qt.KeepAspectRatio)
        self.ui.graphicsView.show()

    def image_viewer(self, item, _):
        if item.parent() == self.ui.treeWidget:
            return None

        file_path = item.text(1)
        if len(file_path) == 0 or not os.path.exists(file_path):
            return None

        self.render_image(file_path)

    def image_open(self, item, _):
        if item.parent() == self.ui.treeWidget:
            return None

        file_path = item.text(1)
        if len(file_path) == 0 or not os.path.exists(file_path):
            return None

        os.startfile(file_path)
