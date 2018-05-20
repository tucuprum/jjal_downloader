from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from bs4 import BeautifulSoup
# noinspection PyUnresolvedReferences
from PIL import Image, ImageTk, ImageChops
from datetime import datetime, timedelta
import pickle
import urllib.parse as urlparse
import requests
import webbrowser
import os
import subprocess
import sys
import re
import imghdr
import time
import base64
import zlib
import textwrap
# noinspection PyUnresolvedReferences
import queue  # required for pyinstaller


# ------------------------------------------- #
# ------------ GLOBAL CONSTANTS ------------- #
# ------------------------------------------- #

# basic information
PROGRAM_VERSION = '5.8.1'
PROGRAM_NICK = 'Bebe'
PROGRAM_TITLE = '짤 다운로더 {} [{}]'.format(PROGRAM_VERSION, PROGRAM_NICK)
RELEASE_DATE_STR = '2018년 5월 18일'

# constants
USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
              'Chrome/51.0.2704.79 Safari/537.36 Edge/14.14393')
USER_AGENT_MOBILE = ('Mozilla/5.0 (Linux; U; Android 2.1-update1; ko-kr; '
                     'Nexus One Build/ERE27) AppleWebKit/530.17 (KHTML, like Gecko) Version/4.0 Mobile Safari/530.17')
TIMEOUT = 15
GUI_PARAM = {'ButtonPadX': 5,
             'ButtonPadY': 5,
             'TablePadX': 5,
             'TablePadY': 5,
             'LabelPadX': 5,
             'LabelPadY': 5,
             'FramePadX': 5,
             'FramePadY': 5}
HELP_LINK = 'http://gall.dcinside.com/board/view/?id=lovelyz&no=1779509'
LOVELYZ_PHOTOS_LINK = 'https://docs.google.com/spreadsheets/d/1qyt2RBDChcvGxoOzATDyzrSyZuKjcMQlCE0DGhq4iGQ/edit#gid=0'
FORBIDDEN_CHAR = '[<>:/\\|?*\"]|[\0-\31]'  # forbidden for file and directory names
FORBIDDEN_STR = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6',
                 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']


# ------------------------------------------- #
# ----- LOADING AND PARSING HTML PAGES ------ #
# ------------------------------------------- #

def refine_url(url):  # refine raw urls into requests-safe ones
    if 'http://' not in url and 'https://' not in url:
        url = 'http://' + url
    m = re.match('http://(?P<naverid>\S+).blog.me/(?P<logNo>\d+)', url)
    if bool(m):
        url = 'http://blog.naver.com/PostView.nhn?blogId='+m.group('naverid')+'&logNo='+m.group('logNo')
    else:
        m2 = re.match('http://blog.naver.com/(?P<naverid>\S+)/(?P<logNo>\d+)', url)
        if bool(m2):
            url = 'http://blog.naver.com/PostView.nhn?blogId='+m2.group('naverid')+'&logNo='+m2.group('logNo') 
    url_safe_chars = '&$+,/:;=?@#'

    return urlparse.quote(url, safe=url_safe_chars, encoding='utf-8')


def load_gall_page(url, make_soup=True):
    # input: url string ==> output:BeautifulSoup (preferred for dcinside: it checks the referer)
    try:
        with requests.session() as s:
            s.headers['Accept'] = 'text/html, application/xhtml+xml, image/jxr, */*'
            s.headers['Accept-Encoding'] = 'gzip, deflate'
            s.headers['Accept-Language'] = 'ko-KR'
            s.headers['Connection'] = 'Keep-Alive'
            s.headers['Host'] = 'gall.dcinside.com'
            s.headers['User-Agent'] = USER_AGENT
            # 'http://gall.dcinside.com/board/lists/?id=lovelyz&page=1&exception_mode=recommend'
            html = s.get(url).text
        if make_soup:
            soup = BeautifulSoup(html, 'lxml')
            return soup
        else:
            return html
    except:
        return None


def load_page(url, make_soup=True):  # input: url string ==> output:BeautifulSoup (generic)
    try:
        with requests.session() as s:
            s.headers['Accept'] = 'text/html, application/xhtml+xml, image/jxr, */*'
            s.headers['Accept-Encoding'] = 'gzip, deflate'
            s.headers['Accept-Language'] = 'ko, en-US; q=0.7, en; q=0.3'
            s.headers['Connection'] = 'Keep-Alive'
            s.headers['User-Agent'] = USER_AGENT
            html = s.get(url, timeout=TIMEOUT).text
        if make_soup:
            soup = BeautifulSoup(html, 'lxml')
            return soup
        else:
            return html
    except:
        return None


def load_mobile_page(url, make_soup=True):  # input: url string ==> output:BeautifulSoup (with mobile user agent)
    try:
        with requests.session() as s:
            s.headers['Accept'] = 'text/html, application/xhtml+xml, image/jxr, */*'
            s.headers['Accept-Encoding'] = 'gzip, deflate'
            s.headers['Accept-Language'] = 'ko, en-US; q=0.7, en; q=0.3'
            s.headers['Connection'] = 'Keep-Alive'
            s.headers['User-Agent'] = USER_AGENT_MOBILE
            html = s.get(url, timeout=TIMEOUT).text
        if make_soup:
            soup = BeautifulSoup(html, 'lxml')
            return soup
        else:
            return html
    except:
        return None


# ------------------------------------------- #
# ---- READING AND WRITING SETTING FILES ---- #
# ------------------------------------------- #

# --- 설정 파일 읽고 쓰기 --- #

def import_settings():  # 설정 메뉴 불러오기
    global last_update
    loaded_options = None  # type: dict
    options_path = 'options.cfg'
    default_setting_list = {'createIndevDir': False, 'destinationFolder': '',
                            'keywordList': [], 'lastUpdate': defaultLU}

    # createIndevDir: 포스트/페이지 별 폴더 생성 여부
    # destinationFolder: 짤 저장 경로
    # keywordList: 중복 필터 키워드 리스트
    # lastUpdate: 가장 최근에 업데이트 확인한 시간

    if not os.path.exists(options_path):
        display_popup_error('옵션 파일이 존재하지 않아 새로 생성합니다.')
        with open(options_path, 'wb') as file:
            pickle.dump(default_setting_list, file)
    try:
        with open(options_path, 'rb') as file:
            loaded_options = pickle.load(file)

    except:
        display_popup_error('옵션 파일을 불러오는 도중에 오류가 발생하였습니다. 옵션 파일을 초기화합니다')
        with open(options_path, 'wb') as file:
            pickle.dump(default_setting_list, file)
    
        loaded_options = default_setting_list

    finally:
        # 기존 파일을 읽어올 경우 기존 파일 값을, 새로 생성할 경우 기본값으로 변수 저장
        create_indiv_dir.set(loaded_options['createIndevDir'])

        destination_folder.set(loaded_options['destinationFolder'])

        del keyword_list[:]
        [keyword_list.append(keyword) for keyword in loaded_options['keywordList']]

        if 'lastUpdate' not in loaded_options.keys():
            last_update = default_setting_list['lastUpdate']
            export_settings()
        else:
            last_update = loaded_options['lastUpdate']

        root.lift()


def export_settings():  # pickle.dump로 저장 값 일괄 덤핑
    options_path = 'options.cfg'
    option_settings = {'createIndevDir': create_indiv_dir.get(), 'destinationFolder': destination_folder.get(),
                       'keywordList': keyword_list, 'lastUpdate': last_update}

    with open(options_path, 'wb') as file:
        pickle.dump(option_settings, file)


# ------------------------------------------- #
# -------- DISPLAYING POPUP MESSAGES -------- #
# ------------------------------------------- #

def display_popup_message(info_message):
    messagebox.showinfo(PROGRAM_TITLE, info_message)


def display_popup_error(error_message):
    messagebox.showwarning(PROGRAM_TITLE, error_message)


def display_popup_yesno(question_message):
    res = messagebox.askyesno(PROGRAM_TITLE, question_message)
    return res


# ------------------------------------------- #
# --------- MAIN GUI WINDOW BUTTONS --------- #
# ------------------------------------------- #

def manual_add_btn():  # 수동 추가
    def list_add():  # 목록 추가
        file_path = filedialog.askopenfilename()
        if file_path == '':
            return 0
        try:
            with open(file_path, 'r') as file:
                text = file.read()
            e.insert(END, '\n'+text)
        except:
            display_popup_error('목록에서 주소를 불러올 수 없습니다. 목록파일이 올바른지 확인해주세요.')
        subroot.lift()

    def manual_add_command():  # 추가된 페이지 분석
        # item_num = len(tree.get_children())
        manual_input = e.get('1.0', 'end').strip()
        try:
            # parsing raw input urls into a url list
            if manual_input == '':
                raise Exception
            loaded_list = re.split('\n', manual_input)

            manual_add_status = Toplevel()

            ttk.Label(manual_add_status, text='선택한 범위에 대해 분석을 진행합니다.', justify=CENTER, anchor=CENTER
                      ).pack(fill=X, in_=manual_add_status, padx=GUI_PARAM['LabelPadX'], pady=GUI_PARAM['LabelPadY'])

            main_progress = ttk.Progressbar(manual_add_status, maximum=100, mode='determinate')
            main_progress.pack(in_=manual_add_status, fill=X, padx=20, pady=10)
        
            # loop: extracting image links from each url page of the url list
            i = 0
            for u in loaded_list:
                try:
                    url = refine_url(u)
                    title, file_list = analyze_page(u)
                    i += 1
                    page = tree.insert('', 'end', values=[url, title, len(file_list), 0])
                    for file in file_list:
                        tree.insert(page, 'end', values=[file, '', '', ''])
                except:
                    pass

                main_progress.step(100/len(loaded_list))
                manual_add_status.update()

            manual_add_status.destroy()
            subroot.destroy()
        except:
            display_popup_error('페이지를 읽어오지 못했습니다. 주소가 올바른지 확인해주세요.')
            subroot.lift()

    # main frame
    subroot = Toplevel()

    # info msg
    ttk.Label(subroot, text='추가할 사이트 주소를 한 줄에 하나씩 적어주세요.', justify=LEFT
              ).pack(padx=GUI_PARAM['LabelPadX'], pady=GUI_PARAM['LabelPadY'])

    # input
    e = Text(subroot, width=50, height=30)
    e.pack(padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'])
    
    # button
    manual_add_btn_frame = ttk.Frame(subroot)
    manual_add_btn_frame.pack()

    b1 = ttk.Button(subroot, text='파일 불러오기', command=list_add)
    b1.grid(row=0, column=0, padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'],
            sticky=E+W, in_=manual_add_btn_frame)

    b2 = ttk.Button(subroot, text='추가', command=manual_add_command)
    b2.grid(row=0, column=1, padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'],
            sticky=E+W, in_=manual_add_btn_frame)


def batch_add_btn():  # 일괄 추가 팝업
    def select_batch():  # 일괄 추가 선택 메뉴 팝업
        ans = batch_choice.get()
        if ans == 'g':
            gall_batch()
        # elif ans == 'i': #인스타그램 일괄 다운로더 현재 비활성화 (개별은 AnalyzePage에서 활성화)
        #    InstaBatch()
        # elif ans == 't': #트위터 일괄 다운로더 현재 비활성화
        #     TwitterBatch()
        elif ans == 'b':
            tistory_batch()
        elif ans == 'p':
            naver_post_batch()
        batch_add_root.destroy()

    batch_add_root = Toplevel()
    batch_choice = StringVar()
    batch_choice.set('g')
    radio_texts = [['디시인사이드 갤러리 (마이너 포함)', 'g'], ['인스타그램', 'i'],
                   ['티스토리 블로그', 'b'], ['네이버 포스트', 'p']]

    ttk.Label(batch_add_root, text='일괄 추가할 사이트를 선택해주세요.'
              ).pack(padx=GUI_PARAM['LabelPadX'], pady=GUI_PARAM['LabelPadY'])
    
    for text, code in radio_texts:
        ttk.Radiobutton(batch_add_root, text=text, variable=batch_choice, value=code
                        ).pack(padx=GUI_PARAM['LabelPadX'], anchor=W)

    ttk.Button(batch_add_root, text='확인', command=select_batch
               ).pack(padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'])


# --- 작업 대기 목록 (tree) 항목 관리 --- #

def delete_item_btn():  # 선택한 아이템 삭제
    raw_selected_items = tree.selection()
    page_index_list = tree.get_children()

    for r in raw_selected_items:
        if r in page_index_list:
            tree.selection_add(tree.get_children(r))
        elif r not in page_index_list and tree.next(r) == '' and tree.prev(r) == '':
            tree.selection_add(tree.parent(r))

    selected_items = tree.selection()
    number_of_selection = len(selected_items)
    if number_of_selection == 0:
        return 0
    
    display_message = '총 ' + str(len(selected_items)) + ' 개 항목을 삭제하시겠습니까?'
    if messagebox.askyesno('항목 삭제', display_message):
        for s in selected_items:
            if not tree.exists(s):
                continue
            elif tree.parent(s) == '':
                tree.delete(s)
            elif tree.parent(s) in selected_items:
                continue
            else:
                itspage = tree.parent(s)
                orig_val = tree.set(itspage)
                tree.item(itspage, value=[orig_val['#1'], orig_val['#2'], int(orig_val['#3'])-1, orig_val['#4']])
                tree.delete(s)
        root.lift()


def clean_item_btn():  # 완료한 내역 삭제
    def reset_selection():
        raw_selected_items = tree.selection()
        for r in raw_selected_items:
            tree.selection_remove(r)

    def clean_indev_items():
        reset_selection()
        for site_index in tree.get_children():
            for jjal_index in tree.get_children(site_index):
                jjal = tree.set(jjal_index)
                if '(100 %)' in jjal['#4']:
                    tree.selection_add(jjal_index)

        for s in tree.selection():
            itspage = tree.parent(s)
            orig_val = tree.set(itspage)
            tree.item(itspage, value=[orig_val['#1'], orig_val['#2'], int(orig_val['#3'])-1, int(orig_val['#4'])-1])
            tree.delete(s)

    def clean_empty_sites():
        reset_selection()
        for site_index in tree.get_children():
            site = tree.set(site_index)
            if int(site['#3']) == 0:
                tree.selection_add(site_index)

        selected_items = tree.selection()
        for s in selected_items:
            tree.delete(s)
            
    clean_indev_items()
    clean_empty_sites()
    reset_selection()

    # def CleanItemOrig():
    #     for site_index in tree.get_children():
    #         site = tree.set(site_index)
    #         if site['#3'] == site['#4']:
    #             tree.selection_add(site_index)
    #             [tree.selection_add(jjal_index) for jjal_index in tree.get_children(site_index)]
    #         else:
    #             for jjal_index in tree.get_children(site_index):
    #                 jjal = tree.set(jjal_index)
    #                 fileSize = jjal['#3']
    #                 processString = jjal['#4']
    #                 if processString == fileSize + ' (100 %)':
    #                     tree.selection_add(jjal_index)
    #
    #     selected_items = tree.selection()
    #
    #     for s in selected_items:
    #         if not tree.exists(s):
    #             continue
    #         elif tree.parent(s) == '':
    #             tree.delete(s)
    #         elif tree.parent(s) in selected_items:
    #             continue
    #         else:
    #             itspage = tree.parent(s)
    #             origVal = tree.set(itspage)
    #             tree.item(itspage, value=[origVal['#1'], origVal['#2'], int(origVal['#3'])-1, int(origVal['#4'])-1])
    #             tree.delete(s)
    #
    #     [tree.delete(site_index) for site_index in tree.get_children() if int(site['#3']) == 0]
    #
    # CleanItemOrig()
    # CleanItemOrig()

    root.lift()


# --- 파일 메뉴 선택 시 드롭다운 메뉴 항목 --- #

def load_list_btn():  # tree 목록 읽어오기
    load_path = filedialog.askopenfilename(initialdir="/", title="파일을 선택하세요",
                                           filetypes=(("짤 다운로더 목록 (*.sav)", "*.sav"), ("모든 파일", "*.*")))
    if load_path == '':
        return 0
    try:
        with open(load_path, 'rb') as file:
            tree_list = pickle.load(file)

        for site, jjalList in tree_list:
            s = tree.insert('', 'end', value=[site['#1'], site['#2'], site['#3'], site['#4']])
            [tree.insert(s, 'end', value=[j['#1'], j['#2'], j['#3'], j['#4']]) for j in jjalList]
    except:
        display_popup_error('불러오는 도중에 오류가 발생하였습니다. 파일을 다시 확인해주세요.')

    root.lift()


def save_list_btn():  # tree 목록 저장하기
    save_path = filedialog.asksaveasfilename(initialdir="/", title="파일을 선택하세요", defaultextension='sav',
                                             filetypes=(("짤 다운로더 목록 (*.sav)", "*.sav"), ("모든 파일", "*.*")))
    tree_list = []
    for site_index in tree.get_children():
        site = tree.set(site_index)
        jjal_list = [tree.set(jjal_index) for jjal_index in tree.get_children(site_index)]
        tree_list.append([site, jjal_list])

    with open(save_path, 'wb') as file:
        pickle.dump(tree_list, file)

    root.lift()


# --- 설정 버튼 --- #

def modify_settings_btn():  # 설정 파일 바꾸기 기능 + 관련 GUI 메뉴 GUI BUTTON
    def set_down_folder_directory():  # 다운로드 폴더 설정
        input_dir = filedialog.askdirectory()
        folder_path_entry.delete(0, END)
        folder_path_entry.insert(0, input_dir)
        setting_window.lift()

    def just_exit():  # 닫기
        import_settings()
        setting_window.destroy()

    def apply_all_settings():  # 적용
        del keyword_list[:]
        [keyword_list.append(word) for word in filter_words.get(0, END)]

        create_indiv_dir.set(create_indev_dir_input.get())
        destination_folder.set(folder_path_entry.get())
        export_settings()

    def confirm_and_exit():  # 적용 후 닫기
        apply_all_settings()
        setting_window.destroy()

    def add_filter():  # 제목 필터 설정
        def exit_add_filter():
            input_text = e.get(1.0, END)
            refined_input_list = set([line.strip() for line in re.split('\n', input_text)
                                      if line.strip() != '' and line.strip() not in keyword_list])
            [filter_words.insert(END, word) for word in refined_input_list]
            add_filter_window.destroy()
            setting_window.lift()

        def just_exit_add_filter():
            add_filter_window.destroy()
            setting_window.lift()

        add_filter_window = Toplevel()
        add_filter_frame = ttk.Frame(add_filter_window)
        add_filter_frame.pack()

        ttk.Label(add_filter_frame, justify=LEFT,
                  text='갤러리 일괄 다운로드 시에 제목에 꼭 들어가야\n하는 키워드를 한 줄에 하나씩 적어주세요.'
                  ).pack(padx=GUI_PARAM['LabelPadX'], pady=GUI_PARAM['LabelPadY'], in_=add_filter_frame)
        e = Text(add_filter_frame, width=37, height=20)
        e.pack(in_=add_filter_frame, padx=GUI_PARAM['LabelPadX'], pady=GUI_PARAM['LabelPadY'])

        filter_button_box = ttk.Frame(add_filter_window)
        filter_button_box.pack()
        ttk.Button(filter_button_box, text='확인', command=exit_add_filter
                   ).grid(column=0, row=0, in_=filter_button_box)
        ttk.Button(filter_button_box, text='취소', command=just_exit_add_filter
                   ).grid(column=1, row=0, in_=filter_button_box)

    def delete_filter():  # 필터 삭제
        if len(filter_words.get(0, END)) == 0:
            return 0
        for item in filter_words.curselection():
            filter_words.delete(item)
        setting_window.lift()

    # --- 설정 메뉴 GUI --- #

    setting_window = Toplevel()
    # optionsPath = 'options.cfg'
    create_indev_dir_input = BooleanVar()
    create_indev_dir_input.set(create_indiv_dir.get())

    setting_tabs = ttk.Notebook(setting_window)
    setting_tabs.pack(in_=setting_window)

    tab1 = ttk.Frame(setting_tabs)
    ttk.Label(tab1, text='짤 다운받는 폴더 설정', justify=LEFT
              ).grid(in_=tab1, row=0, column=0, sticky=W, padx=GUI_PARAM['LabelPadX'], pady=GUI_PARAM['LabelPadY'])

    folder_path_entry = ttk.Entry(tab1, width=40)
    folder_path_entry.grid(in_=tab1, row=2, column=0, sticky=W, 
                           padx=GUI_PARAM['LabelPadX'], pady=GUI_PARAM['LabelPadY'])
    folder_path_entry.insert(END, destination_folder.get())

    ttk.Button(tab1, text='...', command=set_down_folder_directory, width=5
               ).grid(in_=tab1, row=2, column=1, sticky=W, padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'])

    ttk.Checkbutton(tab1, text='사이트 별로 폴더를 생성', variable=create_indev_dir_input
                    ).grid(in_=tab1, row=3, column=0, sticky=W, padx=GUI_PARAM['ButtonPadX'],
                           pady=GUI_PARAM['ButtonPadY'])
    
    tab2 = ttk.Frame(setting_tabs)

    text_box = ttk.Frame(tab2)
    text_box.pack(padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'], side=LEFT)

    esb = ttk.Scrollbar(text_box, orient=VERTICAL)

    filter_words = Listbox(text_box, width=30, height=10, yscrollcommand=esb.set, selectmode=EXTENDED)
    filter_words.pack(side=LEFT, fill=BOTH, expand=1)
    for keyword in keyword_list:
        filter_words.insert(END, keyword)

    esb.config(command=filter_words.yview)
    esb.pack(side=RIGHT, fill=Y)

    button_box = ttk.Frame(tab2)
    button_box.pack(padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'], side=RIGHT)
    ttk.Button(button_box, text='추가', command=add_filter).grid(column=0, row=0, in_=button_box)
    ttk.Button(button_box, text='삭제', command=delete_filter).grid(column=0, row=1, in_=button_box)

    setting_tabs.add(tab1, text='다운로드 폴더')
    setting_tabs.add(tab2, text='제목 필터')

    main_button_box = ttk.Frame(setting_window)
    main_button_box.pack()
    ttk.Button(main_button_box, text='확인', command=confirm_and_exit).grid(column=0, row=0, in_=main_button_box)
    ttk.Button(main_button_box, text='취소', command=just_exit).grid(column=1, row=0, in_=main_button_box)
    ttk.Button(main_button_box, text='적용', command=apply_all_settings).grid(column=2, row=0, in_=main_button_box)


# --- 프로그램 정보 출력 --- #

def show_info():
    info_window = Toplevel()
    info_text = ('{}\n\n초코맛제티 - 러블리즈 갤러리 ({})\n\n- 현재 지원 사이트 -\n'
                 '개별·일괄 모두 지원: 디시인사이드 갤러리, 티스토리 블로그 (일부 제외), 네이버 포스트 \n'
                 '개별 다운로드만 지원: 티스토리 블로그 (일부), 인스타그램, 트위터, 네이버 블로그, 네이버 스타캐스트'
                 ).format(PROGRAM_TITLE, RELEASE_DATE_STR)
    ttk.Label(info_window, text=info_text, justify=CENTER).pack(in_=info_window, padx=20, pady=20)


# ------------------------------------------- #
# ----------- IMAGE URL EXTRACTION ---------- #
# ------------------------------------------- #

def history_add(site):  # 과거 분석 기록에 추가하기
    history_file = 'history.log'
    if not os.path.exists(history_file):
        with open(history_file, 'w') as file:
            file.write(site)
    else:
        with open(history_file, 'r') as file:
            his = file.read()
        if site not in his:
            with open(history_file, 'a') as file:
                file.write('\n' + site)
    
    return None


def history_duplicates(sites):  # 과거 분석 기록 읽어오기
    history_file = 'history.log'
    if not os.path.exists(history_file):
        with open(history_file, 'w') as file:
            file.write('')

    with open('history.log', 'r') as file:
        history_list = re.split('\n', file.read())

    dup = False
    refined_sites = list()
    for site in sites:
        for his in history_list:
            dup = False
            if his == site:
                dup = True
                break
        if not dup:
            refined_sites.append(site)

    return refined_sites


def analyze_page(url):  # 개별 페이지 URL 주소에서 포함된 이미지 주소 추출하여 출력하기

    # 갤 페이지 분석
    if 'dcinside.com' in url:
        soup = load_gall_page(url)
        title = str(soup.title.string.encode('euc-kr', 'ignore').decode('euc-kr')).strip()
        file_list = []

        # files from attachments
        attached_files = soup.find('ul', class_='appending_file')
        file_nos = {}
        if attached_files is not None:
            attached_files = attached_files.find_all('a')
            for file in attached_files:
                file_url = file.get('href')
                file_nos[re.search('php\?id=\S+&no=(?P<imgid>\S+)&f_no', file_url).group('imgid')] = file_url
                
        # files from main contents
        cont = soup.find('div', attrs={'class', 's_write'})
        atags = cont.find_all('a', target='image')

        if len(atags) > 0:
            for a in atags:
                img_url = a.get('href')
                img_id = re.search('php\?id=\S+&no=(?P<imgid>\S+)', img_url).group('imgid')
                if img_id in file_nos.keys():
                    file_list.append(file_nos[img_id])
                else:
                    file_list.append(img_url)

        else:
            imgs = cont.find_all('img')
            for img in imgs:
                if 'dccon.php' in str(img):  # 디시콘 제외
                    continue

                if bool(re.search('imgPop', str(img))):
                    img_url = re.sub('Pop', '', re.split("'", img.get('onclick'))[1])
                    img_id = re.search('php\?id=\S+&no=(?P<imgid>\S+)', img_url).group('imgid')
                    if img_id in file_nos.keys():
                        file_list.append(file_nos[img_id])
                    else:
                        file_list.append(img_url)
                    # if img_id not in file_nos:
                    #    fileList.append(img_url)

                elif bool(re.match('^http\S+', img.get('src'))):
                    img_url = img.get('src')
                    img_id = re.search('php\?id=\S+&no=(?P<imgid>\S+)', img_url).group('imgid')
                    if img_id in file_nos.keys():
                        file_list.append(file_nos[img_id])
                    else:
                        file_list.append(img_url)
                    # i f img_id not in file_nos:
                    #    fileList.append(img_url)
        # fileList += list(set(file_nos.values()))

    # 네이버 블로그 분석
    elif 'blog.naver.com' in url:
        soup = load_page(url)
        title = str(soup.title.string.encode('euc-kr', 'ignore').decode('euc-kr')).strip()
        imgs = soup.find_all('img')
        photo_raw_url_list = [re.sub('postfiles\d+', 'blogfiles', x.get('src')) for x in imgs
                              if '.png' in x.get('src') or '.jpg' in x.get('src')]
        file_list = [re.split('\?type=', x)[0] for x in photo_raw_url_list]

    # 네이버 포스트 분석
    elif 'post.naver.com' in url:
        soup = load_page(url)
        title = str(soup.title.string.encode('euc-kr', 'ignore').decode('euc-kr')
                    ).replace(': 네이버 포스트', '').strip().replace('\n', ' ')
        main_div = soup.find('div', {'id': 'cont', 'class': ['end', '__viewer_container']})
        imgsoup = BeautifulSoup(main_div.script.string, 'lxml')

        file_list = []
        for img_tag in imgsoup.find_all('img'):
            img = img_tag.get('data-src')

            if 'http://gfmarket' in img:
                continue

            srch = re.search('\?type=\S+$', img)  # ?type=w1200 같이 마지막에 붙는 이미지 크기 변수 제거
            if bool(srch):
                file_list.append(img.replace(srch.group(), ''))
            else:
                file_list.append(img)

    # 네이버 뉴스 분석
    elif 'entertain.naver.com' in url:
        soup = load_page(url)
        title = str(soup.title.string.encode('euc-kr', 'ignore').decode('euc-kr')
                    ).replace(':: 네이버 TV연예', '').replace('\n', ' ').strip()
        cont = soup.find('div', {'id': 'articeBody'})

        file_list = []
        for img_tag in cont.find_all('img'):
            img = img_tag.get('src')
            srch = re.search('\?type=\S+$', img)  # ?type=w1200 같이 마지막에 붙는 이미지 크기 변수 제거
            if bool(srch):
                file_list.append(img.replace(srch.group(), ''))
            else:
                file_list.append(img)

    # 인스타그램 분석
    elif 'instagram.com' in url:
        soup = load_page(url)
        owner = re.search('@(?P<owner>\S+)\S*', soup.find('meta', property='og:description').get('content')
                          ).group('owner')
        if bool(re.search('님', owner)):
            owner = re.split('님', owner)[0]
        title = owner
        if soup.find('meta', property='og:video') is None:
            file_list = [soup.find('meta', property='og:image').get('content')]
        else:
            file_list = [soup.find('meta', property='og:video').get('content')]

    # 트위터 페이지 분석
    elif 'twitter.com' in url:
        soup = load_page(url)
        orig_title = str(soup.title.string.encode('euc-kr', 'ignore').decode('euc-kr')).strip()
        title = re.sub(' 님', '', re.sub('트위터의 ', '', re.split(':', orig_title)[0]))

        if soup.find('meta', property='og:video:url') is None:
            file_list = [i.get('src') + ':orig' for i in soup.find_all('img')
                         if i.get('src') is not None and bool(re.search('https://pbs.twimg.com/media/', i.get('src')))]
        else:
            file_list = [soup.find('meta', property='og:video:url').get('content')]

    # 티스토리 분석: 티스토리는 URL에 tistory 가 없는 경우가 종종 있음
    else:
        soup = load_page(url)
        title_list = soup.find_all('title')
        title = (''.join([str(t.string.encode('euc-kr', 'ignore').decode('euc-kr')).strip() + ' - '
                          for t in title_list]))[:-3]
        file_position = soup.find('div', class_='article')
        if file_position is None:
            file_position = soup.find('div', class_='tt_article_useless_p_margin')
        if file_position is None:
            file_position = soup.find('div', class_='etr-etr-content')
        if file_position is None:
            raise Exception
        else:
            file_list = [re.sub('/image/', '/original/', file.get('src')) for file in file_position.find_all('img')
                         if bool(re.match('^http\S+', file.get('src')))]
    
    history_add(url)  # 분석한 URL은 history.log에 추가

    return title, file_list


# ------------------------------------------- #
# ----------- BATCH PAGE ANALYZER ------------#
# ------------------------------------------- #

# --- 갤 게시판에서 개별 게시물/포스트 추출하기 --- #

def gall_batch():
    def get_final_url(raw_url):  # 디시인사이드 리디렉션이 스크립트 형태여서 스크립트에서 URL 직접 추출
        html_data = load_gall_page(raw_url, make_soup=False)
        if html_data.startswith('<script>'):
            redir_url = html_data[33:-12]
            if redir_url == raw_url:
                return raw_url
            else:
                return get_final_url('http://gall.dcinside.com' + redir_url)
        else:
            return raw_url

    def gall_code_search():  # 갤러리 코드 검색
        def find_code():  # 모바일 페이지 내 갤러리 코드 검색 기능을 이용
            gall_list_box.delete(0, END)
            search_keyword = gall_search_keyword_entry.get()
            if search_keyword == '':
                display_popup_error('검색할 키워드가 없습니다. 다시 입력해주세요.')
                gall_search_keyword_entry.delete(0, END)
                gall_code_search_box.lift()
                return 0

            search_url = refine_url('http://m.dcinside.com/search/?search_gall={}'
                                    '&search_type=gall_name'.format('search_keyword'))
            soup = load_mobile_page(search_url)

            try:
                a_list = soup.find('div', class_="searh-result-box").find_all('a')
                del refined_list[:]
                for a in a_list:
                    if 'http://m.dcinside.com/list.php' in a.get('href'):
                        title = ''.join(a.strings).strip()
                        code = re.split('=', a.get('href'))[1]
                        refined_list.append([title, code])
            except:
                display_popup_error('검색 결과 도중에 오류가 발생하였습니다. 검색 키워드를 다시 입력해주세요.')
                gall_search_keyword_entry.delete(0, END)
                gall_code_search_box.lift()
                return 0

            [gall_list_box.insert(END, title) for title, code in refined_list]
            gall_code_search_box.lift()

        def return_code():  # 최종 코드 리턴
            selected_index = gall_list_box.curselection()[0]
            selected_gall_code = refined_list[selected_index][1]

            gall_code.delete(0, END)
            gall_code.insert(0, selected_gall_code)  # gallCode에 저장

            gall_code_search_box.destroy()

        # --- 해당 GUI 코드 --- #

        gall_code_search_box = Toplevel()
        refined_list = []

        ttk.Label(gall_code_search_box, text='검색할 키워드를 입력해주세요.'
                  ).grid(column=0, row=0, in_=gall_code_search_box, sticky=E+W)
        
        gall_search_keyword_entry = ttk.Entry(gall_code_search_box)
        gall_search_keyword_entry.grid(column=0, row=1, in_=gall_code_search_box)

        ttk.Button(gall_code_search_box, text='검색', command=find_code).grid(column=1, row=1)

        ttk.Button(gall_code_search_box, text='확인', command=return_code).grid(column=2, row=1)

        gall_list_box_frame = ttk.Frame(gall_code_search_box)
        gall_list_box_frame.grid(column=0, row=2, columnspan=3, padx=GUI_PARAM['TablePadX'],
                                 pady=GUI_PARAM['TablePadY'], sticky=E+W)

        gall_list_box_scroll_bar = ttk.Scrollbar(gall_list_box_frame, orient=VERTICAL)
        gall_list_box = Listbox(gall_list_box_frame, yscrollcommand=gall_list_box_scroll_bar.set)
        gall_list_box.pack(side=LEFT, fill=BOTH, expand=1)
        gall_list_box_scroll_bar.config(command=gall_list_box.yview)
        gall_list_box_scroll_bar.pack(side=RIGHT, fill=Y)

    def gall_range_analyze():  # 갤 페이지 범위 분석
        def get_last_gall_page(dest_url_inner):  # 갤러리 내 최종 페이지 범위 찾기
            soup_inner = load_gall_page(dest_url_inner)
            page_range_html = soup_inner.find('div', id='dgn_btn_paging')
            end_page_url = page_range_html.find_all('a')[-1].get('href')
            end_page = re.search('page=(?P<pagenum>\d+)', end_page_url).group('pagenum')

            return int(end_page)

        dest_url = get_final_url('http://gall.dcinside.com/' + gall_code.get())
        # gallCode 불러온 후 스크립트 리디렉션의 최종 URL 추출
        gall_url_var.set(dest_url)  # exclude recommendationQ for page range analysis
        if rec_q_input.get():  # 개념글 필터
            dest_url += '&exception_mode=recommend'
        
        try:
            soup = load_gall_page(dest_url)
            if soup.title.string == '디시인사이드 경고창':
                raise Exception
            else:
                selected_gall_title_display.set('선택한 갤러리: ' + soup.title.string +
                                                ('' if not rec_q_input.get() else ' (개념글만)'))
        except:
            display_popup_error('갤러리를 찾을 수 없습니다. 다시 시도해주세요.')
            gall_code.delete(0, END)
            gall_batch_root.lift()
            return 0

        last_page = get_last_gall_page(dest_url)
        last_page_index.set(last_page)
        last_page_display.set('선택 가능한 범위: 1-'+str(last_page))

    def gall_batch_analyze():  # 선택한 범위 내 이미지 URL 추출
        down_range_input = down_range_entry.get()
        gall_url = gall_url_var.get()
        if down_range_input == '' or gall_url == '':  # 다운로드 범위가 없거나 갤 URL이 설정되지 않았으면 취소
            return 0

        gall_batch_status = Toplevel()
        ttk.Label(gall_batch_status, text='선택한 범위에 대해 분석을 진행합니다.', justify=CENTER, anchor=CENTER
                  ).pack(fill=X, in_=gall_batch_status, padx=GUI_PARAM['LabelPadX'], pady=GUI_PARAM['LabelPadY'])

        all_list = []  # 페이지 URL 리스트

        try:
            if not bool(re.match('^[\d, \-]+$', down_range_input)):  # 선택 범위에 숫자, - , , 외 다른 게 있으면 거부
                raise Exception
            page_list = []
            range_split_list = re.split(', ', down_range_input)
            for p in range_split_list:  # 1-4, 10 ==> [1, 2, 3, 4, 10]
                if '-' in p.strip():
                    init, fin = [int(x) for x in re.split('-', p.strip())]
                    page_list += list(range(init, fin+1))
                else:
                    page_list.append(int(p.strip()))

            page_list = set(page_list)
            full_page_range = set(range(1, last_page_index.get()+1))
            if not (page_list < full_page_range or page_list == full_page_range):
                raise Exception

        except:
            display_popup_error('다운 범위를 잘못 입력하셨습니다. 다시 입력해주세요.')
            down_range_entry.delete(0, END)
            gall_batch_status.destroy()
            gall_batch_root.lift()
            return 0

        main_progress = ttk.Progressbar(gall_batch_status, maximum=100, mode='determinate')
        main_progress.pack(in_=gall_batch_status, fill=X, padx=20, pady=10)
        working_status_str_1.set('작업 목록에 추가 중...')
        gall_batch_status.update()

        for p in page_list:  # 각 페이지에 접속해서 페이지 링크 추출
            page_url = gall_url_var.get() + ('&exception_mode=recommend' if rec_q_input.get() else '')\
                       + '&page={}'.format(p)
            try:
                soup = load_gall_page(page_url)
            except:
                continue
            # if pageURLReq.status == 200:
            #     
            # else:
            #     continue

            threads = soup.find('tbody', attrs={'class', 'list_tbody'}).find_all('tr')  # 각 tr 항목마다 갤 제목 등등 저장

            valid_threads = [t for t in threads
                             if t.find('td') is not None
                             and bool(re.match('\d+', t.find('td', class_='t_notice').string))]  # 공지사항 등 제외

            if keyword_list == [] or not apply_filter_q_input.get():
                # 필터가 없거나 필터 적용 클릭 없을 경우 최종 url만 리턴
                all_list += ['http://gall.dcinside.com' + v.find('a').get('href') for v in valid_threads]

            else:  # 제목 필터 적용
                for v in valid_threads:
                    thread_title = ''.join(v.find('td', class_='t_subject').strings)
                    for k in keyword_list:
                        if k in thread_title:
                            all_list.append('http://gall.dcinside.com' + v.find('a').get('href'))
                            continue

            main_progress.step(100/len(page_list))
            gall_batch_status.update()

        # refine &page= part
        all_list = [re.sub('&page=\d+$', '', a) for a in all_list]  # 불필요한 url string 삭제

        main_progress['value'] = 0

        refined_all_list = history_duplicates(all_list)  # 과거 분석 기록과 대조
        dup_n = len(all_list) - len(refined_all_list)

        if dup_n != 0:
            res = display_popup_yesno('기존 다운로드 기록과 겹치는 사이트가 {}개 있습니다. '
                                      '중복된 사이트만 제외하고 받을까요?'.format(dup_n))
            if res:
                all_list = refined_all_list

        for u in all_list:  # 개별 페이지 접속 후 이미지 url 추출 후 tree에 추가
            try:
                url = refine_url(u)
                title, file_list = analyze_page(u)
                page = tree.insert('', 'end', values=[url, title, len(file_list), 0])
                for file in file_list:
                    tree.insert(page, 'end', values=[file, '', '', ''])
            except:
                pass
            finally:
                main_progress.step(100/len(all_list))
                gall_batch_status.update()
        
        gall_batch_status.destroy()
        gall_batch_root.destroy()
        working_status_str_1.set('추가 완료')

    # --- GALL BATCH MAIN WINDOW --- #

    gall_batch_root = Toplevel()
    gall_url_var = StringVar()
    gall_url_var.set('')
    rec_q_input = BooleanVar()
    rec_q_input.set(False)
    apply_filter_q_input = BooleanVar()
    apply_filter_q_input.set(False)

    # --- SELECT GALL CODE --- #

    gall_select_frame = ttk.LabelFrame(gall_batch_root, text='1. 갤러리 및 범위 선택')
    gall_select_frame.pack(fill=BOTH, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'])
    
    # --- 갤러리 선택 프레임 --- #

    gall_select_frame1 = ttk.Frame(gall_select_frame)
    gall_select_frame1.pack(in_=gall_select_frame, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'], fill=X)

    ttk.Label(gall_select_frame1, text='검색할 갤러리 코드: ').grid(column=0, row=0, in_=gall_select_frame1, sticky=W)
    gall_code = ttk.Entry(gall_select_frame1, width=19)
    gall_code.grid(column=1, row=0, in_=gall_select_frame1, sticky=W+E)
    ttk.Button(gall_select_frame1, text='...', command=gall_code_search, width=5
               ).grid(column=2, row=0, sticky=E, in_=gall_select_frame1)

    # --- 페이지 범위 선택 프레임 --- #
    gall_select_frame2 = ttk.Frame(gall_select_frame)
    gall_select_frame2.pack(in_=gall_select_frame, padx=GUI_PARAM['FramePadX'], fill=X)

    ttk.Checkbutton(gall_select_frame2, text="개념글만 다운로드", variable=rec_q_input
                    ).pack(padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'], side=LEFT)
    ttk.Checkbutton(gall_select_frame2, text="제목 필터 적용", variable=apply_filter_q_input
                    ).pack(padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'], side=LEFT)
    
    ttk.Button(gall_select_frame, text="범위 분석", command=gall_range_analyze
               ).pack(padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'], side=BOTTOM)

    # --- PAGE RANGE --- #

    last_page_index = IntVar()
    last_page_index.set(0)
    last_page_display = StringVar()
    last_page_display.set('')

    gall_range_frame = ttk.LabelFrame(gall_batch_root, text='2. 다운로드할 페이지 선택')
    gall_range_frame.pack(fill=BOTH, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'])

    gall_range_frame1 = ttk.Frame(gall_range_frame)
    gall_range_frame1.pack(in_=gall_range_frame, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'], fill=X)

    selected_gall_title_display = StringVar()
    selected_gall_title_display.set('선택한 갤러리: ')

    ttk.Label(gall_range_frame1, textvariable=selected_gall_title_display, justify=LEFT, anchor=W
              ).pack(in_=gall_range_frame1, fill=X)
    ttk.Label(gall_range_frame1, textvariable=last_page_display, justify=LEFT, anchor=W
              ).pack(in_=gall_range_frame1, fill=X)

    gall_range_frame2 = ttk.Frame(gall_range_frame)
    gall_range_frame2.pack(in_=gall_range_frame, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'], fill=X)

    ttk.Label(gall_range_frame2, text='다운 받을 페이지 범위 (예: 1, 2-4): ', justify=LEFT, anchor=W
              ).grid(column=0, row=0, in_=gall_range_frame2, sticky=W)
    down_range_entry = ttk.Entry(gall_range_frame2, width=14)
    down_range_entry.grid(column=1, row=0, in_=gall_range_frame2, sticky=E)
    
    ttk.Button(gall_range_frame, text='페이지 분석', command=gall_batch_analyze
               ).pack(in_=gall_range_frame, padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'])

# def InstaBatch():
#    def InstaRangeAnalyze():
#        url = instaCode.get()
#        nonlocal parsedURLList
#        try:
#            urlsoup = ur.Request(url)
#            soup = MakeSoup(urlsoup)
#            flist = soup.find_all('script', type='text/javascript')
#            for f in flist:
#                if f.string is not None and bool(re.search('window._sharedData', f.string)):
#                    contents = f.string
#            rawCodeList = re.findall('{"code": \S+"',contents)
#            [parsedURLList.append('https://www.instagram.com/p/'+r[10:-1]) for r in rawCodeList]
#            selectedInstaTitleDisplay.set('선택한 인스타그램: '+ soup.title.string.encode('euc-kr','ignore').decode('euc-kr'))
#            lastPageDisplay.set('선택 가능한 범위 (일부분만 지원): 1-'+str(len(parsedURLList)))
#            lastPageIndex.set(len(parsedURLList))
#        except:
#            DisplayError('인스타그램을 읽을 수 없습니다. 다시 시도해주세요.')
#            instaCode.delete(0,END)
#            del parsedURLList[:]        
#        instaBatchRoot.lift()


#    def InstaBatchAnalyze():
#        nonlocal parsedURLList
#        downRangeInput = downRangeEntry.get()
#        if downRangeInput == '' or instaCode.get() == '':
#            return 0

#        instaBatchStatus = Toplevel()
#        ttk.Label(instaBatchStatus,text='선택한 범위에 대해 분석을 진행합니다.',justify=CENTER,anchor=CENTER
#  ).pack(fill=X,in_=instaBatchStatus,padx=GUIParam['LabelPadX'],pady=GUIParam['LabelPadY'])

#        try:
#            if not bool(re.match('^[\d,\- ]+$',downRangeInput)):
#                raise Exception
#            pageList = []
#            rangeSplitList = re.split(',',downRangeInput)
#            for p in rangeSplitList:
#                if '-' in p.strip():
#                    init, fin = [int(x) for x in re.split('-',p.strip())]
#                    pageList += list(range(init,fin+1))
#                else:
#                    pageList.append(int(p.strip()))

#            pageList = set(pageList)
#            fullPageRange = set(range(1,lastPageIndex.get()+1))
#            if not (pageList < fullPageRange or pageList == fullPageRange):
#                raise Exception

#        except:
#            DisplayError('다운 범위를 잘못 입력하셨습니다. 다시 입력해주세요.')
#            downRangeEntry.delete(0,END)
#            instaBatchStatus.destroy()
#            instaBatchRoot.lift()
#            return 0


#        selectedURLList = [parsedURLList[i-1] for i in pageList]

#        mainProgress = ttk.Progressbar(instaBatchStatus,maximum=100,mode='determinate')
#        mainProgress.pack(in_=instaBatchStatus,fill=X,padx=20,pady=10)
#        workingStatusString1.set('작업 목록에 추가 중...')

#        for u in selectedURLList:
#            try:
#                url = RefineURL(u)
#                title, fileList = AnalyzePage(u)
#                page = tree.insert('','end',values=[url,title,len(fileList),0])
#                for f in fileList:
#                    tree.insert(page,'end',text=f,values=[f,'','',''])
#            except:
#                pass

#            mainProgress.step(100/len(selectedURLList))
#            instaBatchStatus.update()

#        instaBatchStatus.destroy()
#        instaBatchRoot.destroy()
#        workingStatusString1.set('추가 완료')


#    instaBatchRoot = Toplevel()
#    parsedURLList = []

#    #### INSTA URL ####

#    instaSelectFrame = ttk.LabelFrame(instaBatchRoot, text='1. 인스타그램 주소 입력')
#    instaSelectFrame.pack(fill=BOTH, padx=GUIParam['FramePadX'], pady=GUIParam['FramePadY'])

#    instaSelectFrame1 = ttk.Frame(instaSelectFrame)
#    instaSelectFrame1.pack(in_=instaSelectFrame, padx=GUIParam['FramePadX'], pady=GUIParam['FramePadY'], fill=X)

#    ttk.Label(instaSelectFrame1,text='검색할 인스타그램 메인 주소: ').grid(column=0,row=0,in_=instaSelectFrame1,sticky=W)
#    instaCode = ttk.Entry(instaSelectFrame1, width=18)
#    instaCode.grid(column=1,row=0,in_=instaSelectFrame1, sticky=W+E)
#    ttk.Button(instaSelectFrame1,text='범위 분석', command=InstaRangeAnalyze).grid(column=2,row=0,sticky=E,
# in_=instaSelectFrame1)


#    #### PAGE RANGE ####

#    lastPageIndex = IntVar()
#    lastPageIndex.set(0)
#    lastPageDisplay = StringVar()
#    lastPageDisplay.set('')

#    instaRangeFrame = ttk.LabelFrame(instaBatchRoot,text='2. 다운로드할 페이지 선택')
#    instaRangeFrame.pack(fill=BOTH, padx=GUIParam['FramePadX'], pady=GUIParam['FramePadY'])

#    instaRangeFrame1 = ttk.Frame(instaRangeFrame)
#    instaRangeFrame1.pack(in_=instaRangeFrame, padx=GUIParam['FramePadX'], pady=GUIParam['FramePadY'], fill=X)

#    selectedInstaTitleDisplay = StringVar()
#    selectedInstaTitleDisplay.set('선택한 인스타그램: ')

#    ttk.Label(instaRangeFrame1, textvariable=selectedInstaTitleDisplay,justify=LEFT,anchor=W
# ).pack(in_=instaRangeFrame1,fill=X)
#    ttk.Label(instaRangeFrame1, textvariable=lastPageDisplay,justify=LEFT,anchor=W).pack(in_=instaRangeFrame1,fill=X)

#    instaRangeFrame2 = ttk.Frame(instaRangeFrame)
#    instaRangeFrame2.pack(in_=instaRangeFrame, padx=GUIParam['FramePadX'], pady=GUIParam['FramePadY'], fill=X)

#    ttk.Label(instaRangeFrame2, text='다운 받을 페이지 범위 (예: 1,2-4): ',justify=LEFT,anchor=W).grid(column=0,row=0,
# in_=instaRangeFrame2,sticky=W)
#    downRangeEntry = ttk.Entry(instaRangeFrame2, width=14)
#    downRangeEntry.grid(column=1,row=0,in_=instaRangeFrame2,sticky=E)
    
#    ttk.Button(instaRangeFrame,text='페이지 분석',command=InstaBatchAnalyze).pack(in_=instaRangeFrame,padx=GUIParam[
# 'ButtonPadX'],pady=GUIParam['ButtonPadY'])


# --- 티스토리 블로그에서 개별 포스트 추출하기 --- #

def tistory_batch():
    def tistory_range_analyze():  # 선택 가능한 범위 분석/설정
        home_url = tistory_code.get().strip()
        if 'http://' not in home_url:
            home_url = 'http://' + home_url
        if not bool(re.match('\S+/$', home_url)):
            home_url += '/'
        if home_url != tistory_code.get():
            tistory_code.delete(0, END)
            tistory_code.insert(0, home_url)
        # try:
        homesoup = load_page(home_url)
        home_title = homesoup.title.string

        category_url = home_url + 'category'  # 선택 가능한 포스트 링크를 category에서 간접적으로 확인함
        soup = load_page(category_url)
        a_list = soup.find_all('a')
        # href_list = []
        last_page = 0
        for a in a_list:
            try:
                curr_page = int(a.get('href').replace('/', ''))  # 포스트 URL이 숫자가 아닐 경우 사용 불가
                if curr_page > last_page:
                    last_page = curr_page
            except:
                pass
        # hrefList = [int(re.sub('/', '', str(a.get('href')))) for a in aList
        # if bool(re.match('^/[0-9]+$', str(a.get('href'))))]
        # hrefEntryList = [str(a.get('href')) for a in aList
        # if bool(re.search('/entry/', str(a.get('href'))))]
        # if hrefList == [] and len(hrefEntryList) > 0:
        #    raise Exception
        if last_page == 0:
            raise ImportError
        last_page_index.set(last_page)
        selected_tistory_title_display.set('선택한 티스토리: ' + home_title)
        last_page_display.set('선택 가능한 범위: 1-'+str(last_page))
            
        # except:
        #    DisplayError('티스토리를 읽을 수 없거나 일괄 다운로드 할 수 없습니다. 다시 시도해주세요.')
        #    tistoryCode.delete(0,END)
        #    lastPageIndex.set(0)
        #    lastPageDisplay.set('')
        
        tistory_batch_root.lift()

    def tistory_batch_analyze():  # 선택한 범위에 대한 분석 실시
        down_range_input = down_range_entry.get()
        tistory_url = tistory_code.get()
        if down_range_input == '' or tistory_url == '':
            return 0

        tistory_batch_status = Toplevel()
        ttk.Label(tistory_batch_status, text='선택한 범위에 대해 분석을 진행합니다.', justify=CENTER, anchor=CENTER
                  ).pack(fill=X, in_=tistory_batch_status, padx=GUI_PARAM['LabelPadX'], pady=GUI_PARAM['LabelPadY'])
        
        try:
            if not bool(re.match('^[\d,\- ]+$', down_range_input)):
                raise Exception
            page_list = []
            range_split_list = re.split(',', down_range_input)
            for p in range_split_list:
                if '-' in p.strip():
                    init, fin = [int(x) for x in re.split('-', p.strip())]
                    page_list += list(range(init, fin+1))
                else:
                    page_list.append(int(p.strip()))
    
            page_list = set(page_list)
            full_page_range = set(range(1, last_page_index.get()+1))
            if not (page_list < full_page_range or page_list == full_page_range):
                raise Exception

        except:
            display_popup_error('다운 범위를 잘못 입력하셨습니다. 다시 입력해주세요.')
            down_range_entry.delete('')
            tistory_batch_status.destroy()
            tistory_batch_root.lift()
            return 0

        # 선택 범위에 해당하는 포스트 URL 목록
        selected_url_list = [tistory_url + str(x) for x in page_list]
        main_progress = ttk.Progressbar(tistory_batch_status, maximum=100, mode='determinate')
        main_progress.pack(in_=tistory_batch_status, fill=X, padx=20, pady=10)
        working_status_str_1.set('작업 목록에 추가 중...')

        # 과거 분석 기록과 대조
        refined_selected_url_list = history_duplicates(selected_url_list)
        dup_n = len(selected_url_list) - len(refined_selected_url_list)

        if dup_n != 0:
            res = display_popup_yesno(('기존 다운로드 기록과 겹치는 사이트가 {}개 있습니다. '
                                       '중복된 사이트만 제외하고 받을까요?').format(dup_n))
            if res:
                selected_url_list = refined_selected_url_list

        # 각 포스트에 접속하여 이미지 URL 추출 후 tree에 저장
        for u in selected_url_list:
            try:
                url = refine_url(u)
                title, file_list = analyze_page(u)
                page = tree.insert('', 'end', values=[url, title, len(file_list), 0])
                for file in file_list:
                    tree.insert(page, 'end', text=file, values=[file, '', '', ''])
            except:
                pass

            main_progress.step(100/len(selected_url_list))
            tistory_batch_status.update()

        tistory_batch_status.destroy()
        tistory_batch_root.destroy()
        working_status_str_1.set('추가 완료')

    tistory_batch_root = Toplevel()
    last_page_index = IntVar()
    last_page_index.set(0)
    last_page_display = StringVar()
    last_page_display.set('')
    selected_tistory_title_display = StringVar()
    selected_tistory_title_display.set('선택한 티스토리: ')

    # --- TISTORY URL FRAME GUI --- #

    tistory_select_frame = ttk.LabelFrame(tistory_batch_root, text='1. 티스토리 주소 입력')
    tistory_select_frame.pack(fill=BOTH, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'])

    tistory_select_frame1 = ttk.Frame(tistory_select_frame)
    tistory_select_frame1.pack(in_=tistory_select_frame, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'], 
                               fill=X)

    ttk.Label(tistory_select_frame1, text='메인 페이지 주소: '
              ).grid(column=0, row=0, in_=tistory_select_frame1, sticky=W+E)
    tistory_code = ttk.Entry(tistory_select_frame1, width=18)
    tistory_code.grid(column=1, row=0, in_=tistory_select_frame1, sticky=W+E)
    tistory_select_frame1.grid_columnconfigure(1, weight=1)
    ttk.Button(tistory_select_frame1, text='...', width=5, command=lambda: webbrowser.open_new(LOVELYZ_PHOTOS_LINK)
               ).grid(column=2, row=0, sticky=E, in_=tistory_select_frame1)
    ttk.Button(tistory_select_frame1, text='범위 분석', command=tistory_range_analyze
               ).grid(column=0, row=1, columnspan=3, in_=tistory_select_frame1,
                      padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'])

    # --- PAGE RANGE FRAME GUI --- #

    tistory_range_frame = ttk.LabelFrame(tistory_batch_root, text='2. 다운로드할 페이지 선택')
    tistory_range_frame.pack(fill=BOTH, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'])

    tistory_range_frame1 = ttk.Frame(tistory_range_frame)
    tistory_range_frame1.pack(in_=tistory_range_frame, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'], fill=X)

    ttk.Label(tistory_range_frame1, textvariable=selected_tistory_title_display, justify=LEFT, anchor=W
              ).pack(in_=tistory_range_frame1, fill=X)
    ttk.Label(tistory_range_frame1, textvariable=last_page_display, justify=LEFT, anchor=W
              ).pack(in_=tistory_range_frame1, fill=X)

    tistory_range_frame2 = ttk.Frame(tistory_range_frame)
    tistory_range_frame2.pack(in_=tistory_range_frame, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'], fill=X)

    ttk.Label(tistory_range_frame2, text='다운 받을 페이지 범위 (클수록 최신) (예: 1, 2-4): ', justify=LEFT, anchor=W
              ).grid(column=0, row=0, in_=tistory_range_frame2, sticky=W)
    down_range_entry = ttk.Entry(tistory_range_frame2, width=14)
    down_range_entry.grid(column=1, row=0, in_=tistory_range_frame2, sticky=E)
    
    ttk.Button(tistory_range_frame, text='페이지 분석', command=tistory_batch_analyze
               ).pack(in_=tistory_range_frame, padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'])


# --- 네이버 포스트 전체 목록에서 개별 포스트 추출하기 --- #

def naver_post_batch():
    def post_range_analyze():  # 선택 가능한 범위 분석/설정
        global aList
        home_url = post_code.get().strip()
        if 'http://' not in home_url:
            home_url = 'http://' + home_url
        # if not bool(re.match('\S+/$', homeURL)):
        #    homeURL += '/'
        if home_url != post_code.get():
            post_code.delete(0, END)
            post_code.insert(0, home_url)
        # try:
        soup = load_page(home_url)
        home_title = soup.find('h2', {'class': 'tit_series'}).string

        soup = load_page(home_url)
        aList = ['http://post.naver.com' + a.get('href') for a in soup.find_all('a', {'class': 'spot_post_area'})]
        last_page = len(aList)
        last_page_index.set(last_page)
        selected_post_title_display.set('선택한 네이버 포스트: ' + home_title)
        last_page_display.set('선택 가능한 범위: 1-' + str(last_page))
            
        # except:
        #    DisplayError('네이버 포스트를 읽을 수 없거나 일괄 다운로드 할 수 없습니다. 다시 시도해주세요.')
        #    postCode.delete(0, END)
        #    lastPageIndex.set(0)
        #    lastPageDisplay.set('')
        
        post_batch_root.lift()

    def post_batch_analyze():  # 선택한 범위에 대한 분석 실시
        global aList
        down_range_input = down_range_entry.get()
        post_url = post_code.get()
        if down_range_input == '' or post_url == '':
            return 0

        post_batch_status = Toplevel()
        ttk.Label(post_batch_status, text='선택한 범위에 대해 분석을 진행합니다.', justify=CENTER, anchor=CENTER
                  ).pack(fill=X, in_=post_batch_status, padx=GUI_PARAM['LabelPadX'], pady=GUI_PARAM['LabelPadY'])
        
        try:
            if not bool(re.match('^[\d, \-]+$', down_range_input)):
                raise Exception
            page_list = []
            range_split_list = re.split(', ', down_range_input)
            for p in range_split_list:
                if '-' in p.strip():
                    init, fin = [int(x) for x in re.split('-', p.strip())]
                    page_list += list(range(init, fin+1))
                else:
                    page_list.append(int(p.strip()))
    
            page_list = set(page_list)
            full_page_range = set(range(1, last_page_index.get()+1))
            if not (page_list < full_page_range or page_list == full_page_range):
                raise Exception

        except:
            display_popup_error('다운 범위를 잘못 입력하셨습니다. 다시 입력해주세요.')
            down_range_entry.delete('')
            post_batch_status.destroy()
            post_batch_root.lift()
            return 0

        # 선택 범위에 해당하는 포스트 URL 목록
        selected_url_list = [aList[x-1] for x in page_list]

        main_progress = ttk.Progressbar(post_batch_status, maximum=100, mode='determinate')
        main_progress.pack(in_=post_batch_status, fill=X, padx=20, pady=10)
        working_status_str_1.set('작업 목록에 추가 중...')

        # 과거 분석 기록과 대조
        refined_selected_url_list = history_duplicates(selected_url_list)
        dup_n = len(selected_url_list) - len(refined_selected_url_list)

        if dup_n != 0:
            res = display_popup_yesno(('기존 다운로드 기록과 겹치는 사이트가 {}개 있습니다. '
                                       '중복된 사이트만 제외하고 받을까요?').format(dup_n))
            if res:
                selected_url_list = refined_selected_url_list

        # 각 포스트에 접속하여 이미지 URL 추출 후 tree에 저장
        for u in selected_url_list:
            try:
                url = refine_url(u)
                title, file_list = analyze_page(u)
                page = tree.insert('', 'end', values=[url, title, len(file_list), 0])
                for file in file_list:
                    tree.insert(page, 'end', text=file, values=[file, '', '', ''])
            except:
                pass

            main_progress.step(100/len(selected_url_list))
            post_batch_status.update()

        post_batch_status.destroy()
        post_batch_root.destroy()
        working_status_str_1.set('추가 완료')

    post_batch_root = Toplevel()
    last_page_index = IntVar()
    last_page_index.set(0)
    last_page_display = StringVar()
    last_page_display.set('')
    selected_post_title_display = StringVar()
    selected_post_title_display.set('선택한 네이버 포스트: ')
    aList = []

    # --- TISTORY URL FRAME GUI --- #

    post_select_frame = ttk.LabelFrame(post_batch_root, text='1. 네이버 포스트 주소 입력')
    post_select_frame.pack(fill=BOTH, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'])

    post_select_frame1 = ttk.Frame(post_select_frame)
    post_select_frame1.pack(in_=post_select_frame, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'], fill=X)

    ttk.Label(post_select_frame1, text='메인 페이지 주소: ').grid(column=0, row=0, in_=post_select_frame1, sticky=W+E)
    post_code = ttk.Entry(post_select_frame1, width=18)
    post_code.grid(column=1, row=0, in_=post_select_frame1, sticky=W+E)
    post_select_frame1.grid_columnconfigure(1, weight=1)
    # ttk.Button(postSelectFrame1, text='...', width=5, command=lambda: webbrowser.open_new(lovelyzPhotosLink)
    # ).grid(column=2, row=0, sticky=E, in_=postSelectFrame1)
    ttk.Button(post_select_frame1, text='범위 분석', command=post_range_analyze
               ).grid(column=0, row=1, columnspan=3, in_=post_select_frame1,
                      padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'])

    # --- PAGE RANGE FRAME GUI --- #

    post_range_frame = ttk.LabelFrame(post_batch_root, text='2. 다운로드할 페이지 선택')
    post_range_frame.pack(fill=BOTH, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'])

    post_range_frame1 = ttk.Frame(post_range_frame)
    post_range_frame1.pack(in_=post_range_frame, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'], fill=X)

    ttk.Label(post_range_frame1, textvariable=selected_post_title_display, justify=LEFT, anchor=W
              ).pack(in_=post_range_frame1, fill=X)
    ttk.Label(post_range_frame1, textvariable=last_page_display, justify=LEFT, anchor=W
              ).pack(in_=post_range_frame1, fill=X)

    post_range_frame2 = ttk.Frame(post_range_frame)
    post_range_frame2.pack(in_=post_range_frame, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'], fill=X)

    ttk.Label(post_range_frame2, text='다운 받을 페이지 범위 (작을수록 최신) (예: 1, 2-4): ', justify=LEFT, anchor=W
              ).grid(column=0, row=0, in_=post_range_frame2, sticky=W)
    down_range_entry = ttk.Entry(post_range_frame2, width=14)
    down_range_entry.grid(column=1, row=0, in_=post_range_frame2, sticky=E)
    
    ttk.Button(post_range_frame, text='페이지 분석', command=post_batch_analyze
               ).pack(in_=post_range_frame, padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'])


# ------------------------------------------- #
# --------- DOWLOAD AND SAVE IMAGES --------- #
# ------------------------------------------- #

def download_items():
    def terminate_download():
        # manual_add.state(['!disabled'])
        batch_add.state(['!disabled'])
        delete_item.state(['!disabled'])
        clean_item.state(['!disabled'])
        check_duplicates.state(['!disabled'])
        continue_download.set(False)
        execution_label.set('실행')
        execution.configure(command=download_items)
        working_status_str_1.set('')
        working_status_str_2.set('')

    def type_to_ext(file):
        format_to_ext = {'jpeg': '.jpg', 'gif': '.gif', 'png': '.png', 'bmp': '.bmp', 'tiff': '.tiff', 'webp': '.webp'}
        image_type = imghdr.what(file)
        if image_type is None:
            with open(file, 'rb') as file:
                file_type = '.jpg' if file.read(16).startswith(b'\xff\xd8\xff') else '.unknown'
        else:
            file_type = format_to_ext[image_type]
        return file_type

    def file_size_converter(size):
        kb = 1024
        mb = kb*kb
        gb = mb*kb

        if size > gb:
            val = str(round(size / gb, 1)) + ' GB'
        elif size > mb:
            val = str(round(size / mb, 1)) + ' MB'
        elif size > kb:
            val = str(round(size / kb, 1)) + ' KB'
        else:
            val = str(round(size)) + ' B'

        return val

    def title_to_folder(title):
        forbidden_names = '[<>:/\\|?*\"]|[\0-\31]'
        forbidden_string = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7',
                            'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']

        if title in forbidden_string:
            folder_name_inner = title + '- 다운로드'
        elif bool(re.search(forbidden_names, title)):
            folder_name_inner = re.sub(forbidden_names, '-', title)
        else:
            folder_name_inner = title
        # if folderName != title:
        #     print(Fore.YELLOW + '  (주의!) 제목에 특수 문자가 있어 다음 폴더에 저장됩니다: ', ConsoleRefine(folderName), Fore.RESET)
        return folder_name_inner.strip()

    def parse_type_header(header):
        kind, file_type = re.split('/', header)
        if kind not in ['video', 'image']:
            ret = 0
        elif file_type == 'jpeg':
            ret = '.jpg'
        else:
            ret = '.'+file_type
        return ret

    # def AlphabetToUTF8(str1, str2): #'be', 'c6' => '아'
    #    return bytes([int('0x'+str1, 16), int('0x'+str2, 16)]).decode('utf-8')

    def download_image(jjal_url, referer):
        update_interval = 0.1

        def gall_euckr_file_name(raw_str):
            def alphabet_to_euckr(str1, str2):  # 'be', 'c6' => '아'
                return bytes([int('0x'+str1, 16), int('0x'+str2, 16)]).decode('euc-kr')

            unicode_binary = re.sub('\\\\\\\\', '\\\\', str(raw_str.encode('unicode_escape'))[2:-1])
            # '\\xa5\\xbe\\xbe...  \\ is one char
            decoded_list = list()
            index = 0
            while True:
                if index >= len(unicode_binary):
                    break
                elif unicode_binary[index:index+2] == '\\x':
                    decoded = (alphabet_to_euckr(unicode_binary[index+2:index+4], unicode_binary[index+6:index+8]))
                    # [a:b] up to b not including b
                    decoded_list.append(decoded)
                    index += 8
                else:
                    decoded_list.append(unicode_binary[index])
                    index += 1
        
            return ''.join(decoded_list)

        def decode_url_name(raw_str):
            return urlparse.unquote(raw_str)

        with requests.session() as s:
            try:
                if 'http://image.dcinside.com/' in jjal_url:
                    # s.headers['Referer'] = jjal_url.replace('download.php', 'viewimage.php')
                    s.headers['Host'] = 'image.dcinside.com'
                    s.headers['Referer'] = jjal_url.replace('viewimage', 'viewimagePop')
                else:
                    s.headers['Referer'] = referer
                s.headers['Accept'] = 'Accept: image/png, image/svg+xml, image/jxr, image/*; q=0.8, */*; q=0.5'
                s.headers['Accept-Encoding'] = 'gzip, deflate'
                s.headers['Accept-Language'] = 'ko, en-US; q=0.7, en; q=0.3'
                s.headers['Connection'] = 'Keep-Alive'
                s.headers['User-Agent'] = USER_AGENT
                resp = s.get(jjal_url, timeout=10, stream=True)
            except:
                tree.set(jjal_index, column=3, value='연결 실패')
                root.update()
                time.sleep(3)
                return None

            try:
                web_file_size = int(resp.headers['Content-Length'])
            except:
                web_file_size = 0

            web_file_ext = parse_type_header(resp.headers['Content-Type'])

            try:
                if 'post.phinf.naver.net' in jjal_url:  # naver post
                    orig_name = decode_url_name(re.split('/', jjal_url)[-1])  # idnetical

                else:
                    web_file_name = resp.headers['Content-Disposition']
                    if 'filename' not in web_file_name:
                        raise NameError

                    elif 'dcinside.com' in jjal_url:  # attachment; filename="1499393942.jpg"
                        orig_name = gall_euckr_file_name(re.split('filename=', web_file_name)[1].replace('"', ''))
                    else:
                        mat = re.search("filename\*=UTF-8''(?P<file>\S+)$", web_file_name)  # test for tistory
                        if bool(mat):
                            orig_name = decode_url_name(mat.group('file'))
                            # inline; filename="1V7A2674.jpg"; filename*=UTF-8''1V7A2674.jpg
                        else:
                            raise NameError

                if orig_name in FORBIDDEN_STR or bool(re.search(FORBIDDEN_CHAR, orig_name)):
                    raise NameError

                new_file_name = os.path.join(folder_name, orig_name)
                if os.path.exists(new_file_name):
                    origname_base, origname_ext = os.path.splitext(new_file_name)
                    new_file_name = os.path.join(folder_name, origname_base + '_' + str(time.time()) + origname_ext)

            except:
                new_file_name = os.path.join(folder_name, str(time.time())) + \
                                ('' if web_file_ext == 0 else web_file_ext)
            
            # Update tree
            tree.set(jjal_index, column=1, value=new_file_name)
            if web_file_size != 0:
                tree.set(jjal_index, column=2, value=file_size_converter(web_file_size))

            temp = os.path.join(folder_name, 'temp')
            start_time = time.time()
            try:
                with open(temp, 'wb') as file:
                    cummul = 0
                    section = 0

                    for buf in resp.iter_content(chunk_size=1024):
                        if not continue_download.get():
                            break
                        file.write(buf)
                        # Check download speed
                        cummul += len(buf)
                        section += len(buf)
                        curr_time = time.time()
                        if curr_time > start_time + update_interval:
                            working_status_str_2.set(file_size_converter(section / (curr_time - start_time)) + '/s')
                            start_time = curr_time
                            section = 0
                            if web_file_size != 0:
                                tree.set(jjal_index, column=3,
                                         value='{} ({}%)'.format(file_size_converter(cummul),
                                                                 round(cummul/web_file_size*100)))
                            root.update()
            except:
                tree.set(jjal_index, column=3, value='다운로드 실패')
                root.update()
                time.sleep(3)
                return None

            if web_file_ext == 0:
                web_file_ext = '.mp4' if bool(re.match('\S+.mp4$', jjal_url)) else type_to_ext(temp)
                new_file_name = os.path.join(folder_name,
                                             os.path.splitext(os.path.basename(new_file_name))[0] + web_file_ext)
                # prevent double extension such as test.jpg.jpg
                tree.set(jjal_index, column=1, value=new_file_name)

            if os.path.exists(new_file_name):
                origname_base, origname_ext = os.path.splitext(os.path.basename(new_file_name))
                new_file_name = os.path.join(folder_name, origname_base + '_' + str(time.time()) + origname_ext)
                tree.set(jjal_index, column=1, value=new_file_name)
        
            tree.set(jjal_index, column=3, value=file_size_converter(cummul)+' (100 %)')
            os.rename(temp, new_file_name)

    # --- SKIP TRIVIAL CASES --- #
    if len(tree.get_children()) == 0:
        display_popup_error('다운로드할 짤이 없습니다.')
        root.lift()
        return 0

    # --- DEACTIVATE TREE MANIPULATION --- #
    # manual_add_btn.state(['disabled'])
    batch_add.state(['disabled'])
    delete_item.state(['disabled'])
    clean_item.state(['disabled'])
    check_duplicates.state(['disabled'])
    execution_label.set('중지')
    execution.configure(command=terminate_download)
    working_status_str_1.set('다운로드 작업 처리 중... ')
    continue_download.set(True)
    root.update()

    # --- EXECUTION --- #
    for site_index in tree.get_children():
        # Termination Check
        if not continue_download.get():
            break
        
        site = tree.set(site_index)

        folder_name = '다운받은 짤' if destination_folder.get() == '' else destination_folder.get()
        if create_indiv_dir.get():
            folder_name = os.path.join(folder_name, title_to_folder(site['#2']))  # page_title
        if not os.path.exists(folder_name):
            os.makedirs(folder_name, exist_ok=True)

        # Process Tree
        i = 0
        for jjal_index in tree.get_children(site_index):
            # Termination Check
            if not continue_download.get():
                break
            # Define jjal-dependent variables
            jjal = tree.set(jjal_index)
            download_image(jjal['#1'], site['#1'])  # url and referer
            i += 1
            tree.set(site_index, column=3, value=i)
            root.update()

    terminate_download()
    display_popup_message('작업을 완료하였습니다.')
    working_status_str_1.set('작업 완료')


# ------------------------------------------- #
# --------------- CHECK UPDATE -------------- #
# ------------------------------------------- #

def check_update(manual=True):
    global last_update

    def check_version(up_to_date):
        global last_update

        curr_v = float(''.join(PROGRAM_VERSION.split('.')))
        if PROGRAM_VERSION.count('.') == 1:
            curr_v /= 10
        else:
            curr_v /= 100

        up_to_date_v = float(''.join(up_to_date.split('.')))
        if up_to_date.count('.') == 1:
            up_to_date_v /= 10
        else:
            up_to_date_v /= 100

        if up_to_date_v > curr_v:
            update_string = ['최신 업데이트가 있습니다. 업데이트하시겠습니까?\n']
            for update in update_info:
                update_string.append('\n')
                update_string.append(update)

            update_q = display_popup_yesno(''.join(update_string))
            return update_q
        else:
            if manual:
                display_popup_error('현재 버전이 최신입니다.')
            last_update = datetime.now()
            export_settings()
            return False

    if datetime.now() < last_update + timedelta(days=1) and not manual:
        return None
    
    log_title = '짤 다운로더 업데이트 로그 - 초코맛제티'
    log_url = 'http://gall.dcinside.com/board/view/?id=lovelyz&no=2811696'
    # bypassQ = False
    try:  
        soup = load_page(log_url)
        contents = soup.find('div', class_='re_gall_box_1').find('div', class_='s_write').strings

        update_info = list()
        latest_ver = ''
        log_start = False
        for line in contents:
            if line.strip() == log_title:
                log_start = True
            if not log_start:
                continue
            if len(update_info) == 0:
                pattern = '>>\s+(?P<version>\d+.\d+(.\d+)?)\s+<(?P<nick>.+)>\s+\((?P<releaseDate>\d{4}.\d{2}.\d{2})\)'
                mat = re.match(pattern, line)
                if bool(mat):
                    latest_ver = mat.group('version')
                    update_info.append(line)
                    continue
            else:
                if '>>' == line[:2]:
                    break
                elif '-' == line[:1]:
                    update_info.append(line)
                    continue

        ret = check_version(latest_ver)
    except:
        display_popup_error('업데이트 확인 중에 문제가 발생하였습니다.')
        return None
        
    if not ret:
        return None

    new_url = ('https://dl.dropboxusercontent.com/s/zk0f8jf21di6n93/'
               '%EC%A7%A4%20%EB%8B%A4%EC%9A%B4%EB%A1%9C%EB%8D%94.exe?dl=0')
    try:
        resp = requests.get(new_url)
        new_name = os.path.basename(sys.argv[0])
        with open(new_name + '.temp', 'wb') as file:
            for buf in resp.iter_content():
                file.write(buf)
    except:
        display_popup_error('새 버전 다운로드 중에 문제가 발생하였습니다. 업데이트를 종료합니다.')
        return None

    try:
        batch = 'jdwnldr_updater.bat'
        # taken from youtube-dl
        output = ('@echo off\n'
                  'ping 127.0.0.1 -n 5 -w 5000 > NUL\n'
                  'del "{}"\n'
                  'ren "{}.temp" "{}" > NUL\n'
                  'echo 짤 다운로더 업데이트를 완료하였습니다. (현재 버전:{})\n'
                  'start /b "" "{}"\n'
                  'start /b "" cmd /c del "%~f0"&exit /b').format(new_name, new_name, new_name, latest_ver, new_name)
        with open(batch, 'w') as file:
            file.write(output)

        subprocess.Popen([batch])
        last_update = datetime.now()
        export_settings()
        root.destroy()

    except:
        display_popup_error('업데이트 중에 문제가 발생하였습니다. 업데이트를 종료합니다.')
        return None


# ------------------------------------------- #
# ------------- 중복이면말좀해주지 ------------ #
# ------------------------------------------- #

def check_duplicate():
    def list_duplicates():
        def file_path_list(target_dir):  # 하위 모든 파일 목록
            file_list = list()
            for directory, subfolders, files in os.walk(target_dir):
                for file_name in files:
                    file_list.append(os.path.join(directory, file_name))

            return file_list

        def filter_duplicates():  # 중복된 파일 이동하기
            for dupfile, origfile in dup_list:
                try:
                    dupbasename = os.path.basename(dupfile)
                    i = 0
                    newname_orig_base, newname_orig_ext = os.path.splitext(dupbasename)
                    newname_base = newname_orig_base
                    newname_ext = newname_orig_ext
                    while True:
                        i += 1
                        newname = newname_base + newname_ext
                        newname_full = os.path.join(dup_folder, newname)
                        if os.path.exists(newname_full):
                            newname_base = '{}-dup-{}'.format(newname_orig_base, i)  # 이동 시 덮어쓰기 방지
                            continue
                        else:
                            os.rename(dupfile, newname_full)
                            break
                except:
                    display_popup_error('다음 파일을 이동하는 도중에 문제가 발생하였습니다: {}'.format(dupfile))

            display_popup_error('중복된 짤을 모두 이동하였습니다.')
            os.startfile(dup_folder)

        tgt_dir = dest_folder.get()  # 검사 대상 폴더
        dir_list = file_path_list(tgt_dir)  # 위 폴더 내 모든 파일

        # GUI VALUES
        list_dupl_status = Toplevel()
        list_dupl_text = StringVar()
        progressbar_var = DoubleVar()
        progressbar_var.set(0.0)

        # Using progress bar to display analysis status
        list_dupl_text.set('선택한 폴더에 대해 분석합니다.')
        ttk.Label(list_dupl_status, textvariable=list_dupl_text, justify=CENTER, anchor=CENTER
                  ).pack(fill=X, in_=list_dupl_status, padx=GUI_PARAM['LabelPadX'], pady=GUI_PARAM['LabelPadY'])

        main_progress = ttk.Progressbar(list_dupl_status, maximum=100, mode='determinate', variable=progressbar_var)
        main_progress.pack(in_=list_dupl_status, fill=X, padx=20, pady=10)

        # 파일 해시 리스트 dict형
        hash_list = dict()
        pre_dup_list = dict()

        for file in dir_list:
            try:
                with open(file, 'rb') as f_point:
                    crc = zlib.crc32(f_point.read())  # crc32 값 추출
            except:
                pass
            if crc in hash_list:  # 기존 hashList 내 동일 hash 존재 여부 확인
                orig_file = hash_list[crc]
                if orig_file in list(pre_dup_list.keys()):  # 존재할 경우, 1차 필터 목록에 추가
                    pre_dup_list[orig_file].append(file)
                else:
                    pre_dup_list[orig_file] = [file]  # 존재하지 않을 경우, hashList에 해당 파일 추가
            else:
                hash_list[crc] = file

            main_progress.step(100/len(dir_list))
            list_dupl_status.update()

        # gui 리셋
        list_dupl_text.set('중복된 짤을 다시 확인하고 있습니다.')
        progressbar_var.set(0.0)
        list_dupl_status.update()

        # 1차 crc hash 충돌 파일에서 픽셀간 2차 비교 실시
        for orig_file in list(pre_dup_list.keys()):
            try:
                orig_image = Image.open(orig_file)
            except:
                continue
            for dup in pre_dup_list[orig_file]:
                try:
                    dup_image = Image.open(dup)
                except:
                    continue

                iden_q = ImageChops.difference(orig_image, dup_image).getbbox() is None  # 픽셀 단위 비교
                if iden_q:  # 픽셀단위로 일치할 경우 최종 중복으로 확인 후 dupList에 추가
                    dup_list.append([dup, orig_file])
                else:  # crc는 일치하였으나 픽셀단위로 다를 경우 susList에 추가
                    sus_list.append([dup, orig_file])

            main_progress.step(100/len(list(pre_dup_list.keys())))
            list_dupl_status.update()

        list_dupl_status.destroy()

        if len(dup_list) == 0:
            display_popup_error('중복된 짤을 찾을 수 없습니다.')
            quit_chck_dupl()
            return None

        # 중복된 짤 저장하는 폴더 생성
        tgt_dir = dest_folder.get()
        dup_folder = os.path.join(tgt_dir, '중복된 짤')
        if not os.path.exists(dup_folder):
            os.mkdir(dup_folder)
    
        # 중복 검사 결과 보고서 작성
        work_time = re.sub(':', '_', datetime.now().isoformat())
        result_save = os.path.join(dup_folder, '분석결과_' + work_time + '.txt')

        output_string = '중복짤\t원본짤\n' + ''.join([''.join([dupfile, '\t', origfile, '\n'])
                                                for dupfile, origfile in dup_list])
        with open(result_save, 'w') as file:
            file.write(output_string)
       
        os.startfile(result_save)  # 중복 결과 정리한 txt 파일 열기
        if len(sus_list) > 0:
            sus_result_save = os.path.join(dup_folder, '의심결과_' + work_time + '.txt')
            output_string = '의심짤\t원본짤\n' + ''.join([''.join([dupfile, '\t', origfile, '\n'])
                                                    for dupfile, origfile in sus_list])
            with open(sus_result_save, 'w') as file:
                file.write(output_string)
            
            query_string = (
                '총 {} 개의 짤이 중복된 것을 확인하였으며, 중복된 파일 목록은 "분석결과_{}.txt"에 저장하였습니다.\n'
                '총 {} 개의 짤은 추가로 확인이 필요하며 "의심결과_{}.txt"를 확인해주세요.\n\n'
                '중복된 짤을 모두 "중복된 짤" 폴더로 이동하시겠습니까?'
            ).format(len(dup_list), work_time, len(sus_list), work_time)

        else:
            query_string = (
                '총 {} 개의 짤이 중복된 것을 확인하였으며, 중복된 파일 목록은 "분석결과_{}.txt"에 저장하였습니다.\n\n'
                '중복된 짤을 모두 "중복된 짤" 폴더로 이동하시겠습니까?'
            ).format(len(dup_list), work_time)

        if display_popup_yesno(textwrap.dedent(query_string)):
            filter_duplicates()

        quit_chck_dupl()

    def set_down_folder_directory():
        input_dir = filedialog.askdirectory()
        dest_folder.delete(0, END)
        dest_folder.insert(0, input_dir)
        chck_dupl_root.lift()
        
    def forbid_other_actions():
        # manual_add_btn.state(['disabled'])
        batch_add.state(['disabled'])
        delete_item.state(['disabled'])
        clean_item.state(['disabled'])
        execution.state(['disabled'])
        check_duplicates.state(['disabled'])
        continue_download.set(False)
        working_status_str_1.set('중복이면말좀해주지 실행 중...')
        root.update()

    def quit_chck_dupl():
        # manual_add_btn.state(['!disabled'])
        batch_add.state(['!disabled'])
        delete_item.state(['!disabled'])
        clean_item.state(['!disabled'])
        execution.state(['!disabled'])
        check_duplicates.state(['!disabled'])
        continue_download.set(True)
        working_status_str_1.set('')
        root.update()
        chck_dupl_root.destroy()

    # --- CHECK DUPLICATE MAIN WINDOW --- #

    chck_dupl_root = Toplevel()
    chck_dupl_root.protocol('WM_DELETE_WINDOW', quit_chck_dupl)
    destination_folder_2 = StringVar()
    destination_folder_2.set('')
    dup_list = list()
    sus_list = list()

    forbid_other_actions()

    chck_dupl_frame = ttk.LabelFrame(chck_dupl_root, text='중복 검사 폴더 입력')
    chck_dupl_frame.pack(fill=BOTH, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'])

    chck_dupl_frame1 = ttk.Frame(chck_dupl_frame)
    chck_dupl_frame1.pack(in_=chck_dupl_frame, padx=GUI_PARAM['FramePadX'], pady=GUI_PARAM['FramePadY'], fill=X)

    ttk.Label(chck_dupl_frame1, text='검사 대상 폴더'
              ).grid(column=0, row=0, columnspan=2, in_=chck_dupl_frame1, sticky=W+E)

    dest_folder = ttk.Entry(chck_dupl_frame1, width=40)
    dest_folder.grid(column=0, row=1, in_=chck_dupl_frame1, sticky=W+E)
    dest_folder.insert(END, destination_folder_2.get())

    ttk.Button(chck_dupl_frame1, text='...', command=set_down_folder_directory, width=5
               ).grid(row=1, column=1, sticky=W, in_=chck_dupl_frame1,
                      padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'])

    ttk.Button(chck_dupl_frame1, text='중복 검사', command=list_duplicates
               ).grid(column=0, row=2, columnspan=2, in_=chck_dupl_frame1,
                      padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'])


# ------------------------------------------- #
# ------------- GUI WINDOW MAIN ------------- #
# ------------------------------------------- #

# icon in base64
icon = '''

AAABAAUAEBAAAAEAIABoBAAAVgAAABgYAAABACAAiAkAAL4EAAAgIAAAAQAgAKgQAABGDgAAMDAAAAEAIACoJQAA7h4AAHh1AAAB
AAgAUEIAAJZEAAAoAAAAEAAAACAAAAABACAAAAAAAAAEAACHHQAAhx0AAAAAAAAAAAAA0tH4/9LR+P/R0Pj/0dD4/9HQ+P/R0Pj/
0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/S0fj/0tH4/9LR+P/V1Pj/3Nv6/9zc+v/c2/r/3Nv6/9zb+v/c2/r/3Nv6
/9zb+v/c2/r/3Nv6/9zc+v/b2/n/1NP4/9LR+P/R0Pj/3dz6//v7/v/9/f///f3///39///9/f///f3///39///9/f///f3///39
///9/f//+fn+/9nY+f/R0Pj/0dD4/97d+v/+/v///////////////////v7///j4/v/39/7//f3///////////////////v7/v/a
2fn/0dD4/9HQ+P/e3fr//v3/////////////+fn+/+Lh+v/X1vn/19b5/93d+v/z8/3////////////7+/7/2tn5/9HQ+P/R0Pj/
3t36//79/////////v7//+Pi+//V1Pj/7u38//Pz/f/b2vn/2tn5//r6/v//////+/v+/9rZ+f/R0Pj/0dD4/97d+v/+/f//////
//z8///a2fn/3t36//7+////////6en8/9PS+P/19f3///////v7/v/a2fn/0dD4/9HQ+P/e3fr//v3////////+/v//4uH6/9jX
+f/y8v3/9vb+/97e+v/Z2Pn/+fn+///////7+/7/2tn5/9HQ+P/R0Pj/3t36//79//////////////f3/v/Y1/n/1dT5/9jX+f/U
0/j/7u78////////////+/v+/9rZ+f/R0Pj/0dD4/97d+v/+/f/////////////t7fz/1dT4/+3s/P/09P3/2dj5/+Lh+v/+/v//
//////v7/v/a2fn/0dD4/9HQ+P/e3fr//v3/////////////5OT7/9XU+P/49/7//v7//93d+v/Z2fn//Pz////////7+/7/2tn5
/9HQ+P/R0Pj/3t36//79//////////////Hw/f/V1Pj/3t36/+Hh+v/U0/j/5ub7////////////+/v+/9rZ+f/R0Pj/0dD4/97d
+v/+/f/////////////+/v//8fH9/+Pj+//i4fr/7e38//z8//////////////v7/v/a2fn/0dD4/9HQ+P/e3fr//v7/////////
///////////////////////////////////////////////7+/7/2tn5/9HQ+P/S0fj/19b5/+Xl+//m5vv/5ub7/+bm+//m5vv/
5ub7/+bm+//m5vv/5ub7/+bm+//m5vv/5OT7/9XU+f/S0fj/0tH4/9LR+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4
/9HQ+P/R0Pj/0dD4/9HQ+P/S0fj/0tH4/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAoAAAAGAAAADAAAAABACAAAAAAAAAJAACHHQAAhx0AAAAAAAAAAAAA0tH4/9LR+P/S0fj/0tH4/9LR+P/S
0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/
0tH4/9LR+P/S0fj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4
/9HQ+P/R0Pj/0tH4/9LR+P/S0fj/0tH4/9LR+P/X1vn/3976/9/f+v/f3/r/39/6/9/f+v/f3/r/39/6/9/f+v/f3/r/39/6/9/f
+v/f3/r/39/6/9/f+v/f3/r/39/6/9/f+v/e3vr/1dT4/9LR+P/S0fj/0tH4/9HQ+P/h4fr//v7///7+///+/v///v7///7+///+
/v///v7///7+///+/v///v7///7+///+/v///v7///7+///+/v///v7///7+///7+/7/29r5/9HQ+P/S0fj/0tH4/9HQ+P/i4fr/
///////////////////////////////////////////////////////////////////////////////////////////8/P//29r5
/9HQ+P/S0fj/0tH4/9HQ+P/i4fr///////////////////////////////////////v7/v/29f7/9fT9//n5/v/+/v//////////
///////////////////8/P//29r5/9HQ+P/S0fj/0tH4/9HQ+P/i4fr////////////////////////////9/f//6+v8/9ra+f/U
0/j/09L4/9jX+f/k5Pv/+Pj+///////////////////////8/P//29r5/9HQ+P/S0fj/0tH4/9HQ+P/i4fr/////////////////
//////7+///o5/v/0tH4/9LR+P/d3Pr/4N/6/9bV+f/R0Pj/29v5//n4/v/////////////////8/P//29r5/9HQ+P/S0fj/0tH4
/9HQ+P/i4fr///////////////////////b2/v/W1fn/0tH4/+bl+//9/f///v7///Pz/f/X1vn/0dD4/+jn+///////////////
///8/P//29r5/9HQ+P/S0fj/0tH4/9HQ+P/i4fr//////////////////////+/v/P/S0fj/1dT4//X1/f////////////7+///h
4Pr/0dD4/9/e+v/+/v/////////////8/P//29r5/9HQ+P/S0fj/0tH4/9HQ+P/i4fr///////////////////////Hw/f/T0fj/
1NP4//T0/f////////////39///f3vr/0c/4/+Df+v/+/v/////////////8/P//29r5/9HQ+P/S0fj/0tH4/9HQ+P/i4fr/////
//////////////////r6/v/b2vn/0dD4/9/f+v/09P3/9/f+/+rq/P/U0/j/09L4/+7t/P/////////////////8/P//29r5/9HQ
+P/S0fj/0tH4/9HQ+P/i4fr////////////////////////////19f3/2tr5/9HQ+P/U0/j/1dT4/9LR+P/T0vj/6en8//7+////
///////////////8/P//29r5/9HQ+P/S0fj/0tH4/9HQ+P/i4fr////////////////////////////19f3/2Nj5/9LR+P/f3vr/
5OP7/9fW+f/T0vj/5+b7//7+///////////////////8/P//29r5/9HQ+P/S0fj/0tH4/9HQ+P/i4fr/////////////////////
//7+///g4Pr/0dD4/9/e+v/8/P////////Dv/f/T0vj/1NP4//T0/f/////////////////8/P//29r5/9HQ+P/S0fj/0tH4/9HQ
+P/i4fr///////////////////////v7/v/Z2Pn/0dD4/+fm+/////////////f2/v/V1Pn/0tH4/+7t/P/////////////////8
/P//29r5/9HQ+P/S0fj/0tH4/9HQ+P/i4fr///////////////////////39///e3fr/0dD4/97d+v/5+f7//Pz//+vq/P/T0vj/
09L4//Ly/f/////////////////8/P//29r5/9HQ+P/S0fj/0tH4/9HQ+P/i4fr////////////////////////////w8P3/1dT4
/9HQ+P/Y1/n/2tn5/9PS+P/S0fj/4uH7//39///////////////////8/P//29r5/9HQ+P/S0fj/0tH4/9HQ+P/i4fr/////////
///////////////////+/v//8fD9/9/e+v/Y1/n/19b5/9zb+v/q6vz/+/v+///////////////////////8/P//29r5/9HQ+P/S
0fj/0tH4/9HQ+P/i4fr///////////////////////////////////////39///6+v7/+fn+//z8////////////////////////
///////////8/P//29r5/9HQ+P/S0fj/0tH4/9HQ+P/i4fr/////////////////////////////////////////////////////
///////////////////////////////////////8/P//29r5/9HQ+P/S0fj/0tH4/9LR+P/c2/r/7+78/+/v/P/v7/z/7+/8/+/v
/P/v7/z/7+/8/+/v/P/v7/z/7+/8/+/v/P/v7/z/7+/8/+/v/P/v7/z/7+/8/+/v/P/t7fz/2Nf5/9LR+P/S0fj/0tH4/9LR+P/S
0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/
0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4
/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAKAAAACAAAABAAAAAAQAgAAAAAAAA
EAAAhx0AAIcdAAAAAAAAAAAAANLR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/
0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4
/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR
+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0dD4/9HQ+P/R
0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/
0dD4/9HQ+P/R0Pj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9nY+f/j4vr/4uL6/+Li+v/i4vr/4uL6/+Li+v/i4vr/4uL6
/+Li+v/i4vr/4uL6/+Li+v/i4vr/4uL6/+Li+v/i4vr/4uL6/+Li+v/i4vr/4uL6/+Li+v/i4vr/4uL6/+Lh+v/W1fn/0tH4/9LR
+P/S0fj/0tH4/9LR+P/R0Pj/5uX7////////////////////////////////////////////////////////////////////////
/////////////////////////////////////////////////////Pz//9zc+v/R0Pj/0tH4/9LR+P/S0fj/0tH4/9HQ+P/m5fv/
////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////9/f//3Nz6/9HQ+P/S0fj/0tH4/9LR+P/S0fj/0dD4/+bl+///////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////39///c
3Pr/0dD4/9LR+P/S0fj/0tH4/9LR+P/R0Pj/5uX7//////////////////////////////////////////////////7+///5+f7/
8/P9//Ly/f/29v7//Pz//////////////////////////////////////////////f3//9zc+v/R0Pj/0tH4/9LR+P/S0fj/0tH4
/9HQ+P/m5fv////////////////////////////////////////////19P3/4uH6/9fW+f/U0/j/09L4/9XU+P/c2/r/7Ov8//z7
/v/////////////////////////////////9/f//3Nz6/9HQ+P/S0fj/0tH4/9LR+P/S0fj/0dD4/+bl+///////////////////
////////////////////7+/9/9bW+f/R0Pj/0dD4/9LR+P/T0vj/0tH4/9HQ+P/S0fj/4N/6//r6/v//////////////////////
//////39///c3Pr/0dD4/9LR+P/S0fj/0tH4/9LR+P/R0Pj/5uX7//////////////////////////////////b2/v/X1vn/0dD4
/9LR+P/c3Pr/7u78//Hx/f/o5/v/1tX5/9LR+P/R0Pj/5OP7//7+/////////////////////////f3//9zc+v/R0Pj/0tH4/9LR
+P/S0fj/0tH4/9HQ+P/m5fv/////////////////////////////////5+b7/9HQ+P/S0fj/2tn5//j4/v/////////////////u
7fz/09L4/9LR+P/W1fn/9vb+///////////////////////9/f//3Nz6/9HQ+P/S0fj/0tH4/9LR+P/S0fj/0dD4/+bl+///////
//////////////////////79///e3vr/0dD4/9HQ+P/n5vv///////////////////////r6/v/Z2Pn/0tH4/9LR+P/v7/z/////
//////////////////39///c3Pr/0dD4/9LR+P/S0fj/0tH4/9LR+P/R0Pj/5uX7/////////////////////////////f3//93d
+v/R0Pj/0tH4/+np/P//////////////////////+/v+/9ra+f/R0Pj/0tH4/+7u/P///////////////////////f3//9zc+v/R
0Pj/0tH4/9LR+P/S0fj/0tH4/9HQ+P/m5fv/////////////////////////////////5eT7/9HQ+P/R0Pj/4eD6//39////////
///////////08/3/1dT4/9LR+P/U0/j/8/P9///////////////////////9/f//3Nz6/9HQ+P/S0fj/0tH4/9LR+P/S0fj/0dD4
/+bl+//////////////////////////////////19P3/1tX5/9HQ+P/T0vj/5OT7//T0/f/39/7/8O/9/9va+f/S0fj/0dD4/+Hg
+v/9/f////////////////////////39///c3Pr/0dD4/9LR+P/S0fj/0tH4/9LR+P/R0Pj/5uX7////////////////////////
///////////////w8P3/2tn5/9LR+P/S0fj/1NP4/9XU+P/T0vj/0tH4/9PS+P/h4Pr/+fn+////////////////////////////
/f3//9zc+v/R0Pj/0tH4/9LR+P/S0fj/0tH4/9HQ+P/m5fv///////////////////////////////////////z8///i4fr/0tH4
/9LR+P/T0vj/1dT4/9LR+P/S0fj/1NT4/+7t/P/////////////////////////////////9/f//3Nz6/9HQ+P/S0fj/0tH4/9LR
+P/S0fj/0dD4/+bl+//////////////////////////////////+/v//5+b7/9LR+P/S0fj/29r5//Hx/f/39/7/6un8/9XU+P/S
0fj/1tX5//Tz/f////////////////////////////39///c3Pr/0dD4/9LR+P/S0fj/0tH4/9LR+P/R0Pj/5uX7////////////
//////////////////////j4/v/X1vn/0tD4/9TT+P/x8f3////////////+/v//5OP7/9HQ+P/R0Pj/4+L7//7+////////////
/////////////f3//9zc+v/R0Pj/0tH4/9LR+P/S0fj/0tH4/9HQ+P/m5fv/////////////////////////////////8vL9/9PS
+P/S0fj/1tX5//j4/v/////////////////q6vz/0tH4/9HQ+P/d3Pr//f3////////////////////////9/f//3Nz6/9HQ+P/S
0fj/0tH4/9LR+P/S0fj/0dD4/+bl+//////////////////////////////////09P3/1NP4/9LR+P/V1Pj/9fT9////////////
/////+Xk+//R0Pj/0dD4/97d+v/9/f////////////////////////39///c3Pr/0dD4/9LR+P/S0fj/0tH4/9LR+P/R0Pj/5uX7
//////////////////////////////////z7/v/c2/r/0dD4/9LR+P/e3vr/8vL9//X1/f/r6vz/1tX5/9LR+P/S0fj/6en8////
/////////////////////////f3//9zc+v/R0Pj/0tH4/9LR+P/S0fj/0tH4/9HQ+P/m5fv/////////////////////////////
//////////Hw/f/V1Pn/0dD4/9LR+P/T0vj/1NT4/9LR+P/R0Pj/0tH4/9/e+v/7+v7////////////////////////////9/f//
3Nz6/9HQ+P/S0fj/0tH4/9LR+P/S0fj/0dD4/+bl+/////////////////////////////////////////7///Hx/f/d3Pr/1NP4
/9LR+P/S0fj/09L4/9jY+f/o5/v/+vr+//////////////////////////////////39///c3Pr/0dD4/9LR+P/S0fj/0tH4/9LR
+P/R0Pj/5uX7//////////////////////////////////////////////////z8/v/19P3/7+78/+7u/P/y8f3/+fn+////////
/////////////////////////////////////f3//9zc+v/R0Pj/0tH4/9LR+P/S0fj/0tH4/9HQ+P/m5fv/////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////
///////9/f//3Nz6/9HQ+P/S0fj/0tH4/9LR+P/S0fj/0dD4/+bm+///////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////39///c3Pr/0dD4/9LR+P/S
0fj/0tH4/9LR+P/R0Pj/4uL6//b2/v/29v7/9vb+//b2/v/29v7/9vb+//b2/v/29v7/9vb+//b2/v/29v7/9vb+//b2/v/29v7/
9vb+//b2/v/29v7/9vb+//b2/v/29v7/9vb+//b2/v/29v7/9PT9/9ra+f/S0Pj/0tH4/9LR+P/S0fj/0tH4/9LR+P/T0/j/1dT4
/9XU+P/V1Pj/1dT4/9XU+P/V1Pj/1dT4/9XU+P/V1Pj/1dT4/9XU+P/V1Pj/1dT4/9XU+P/V1Pj/1dT4/9XU+P/V1Pj/1dT4/9XU
+P/V1Pj/1dT4/9XU+P/V1Pj/09L4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S
0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/
0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4
/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P8AAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACgAAAAwAAAAYAAAAAEAIAAAAAAAACQAAIcdAACHHQAA
AAAAAAAAAADS0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4
/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR
+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S
0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/
0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4
/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR
+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S
0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/
0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4
/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR
+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S
0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/
0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4
/9LR+P/S0fj/0tH4/+Hg+v/p6fz/6en7/+np+//p6fv/6en7/+np+//p6fv/6en7/+np+//p6fv/6en7/+np+//p6fv/6en7/+np
+//p6fv/6en7/+np+//p6fv/6en7/+np+//p6fv/6en7/+np+//p6fv/6en7/+np+//p6fv/6en7/+np+//p6fv/6en7/+np+//p
6fv/6en7/+jo+//Z2Pn/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR
+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////
////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////39///f3/r/0dD4/9LR+P/S
0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u
/P//////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////39///f3/r/
0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////////////////////////////
//////////////////////////////////7+///6+v7/9PP9/+7t/P/t7Pz/7+/9//b2/v/8/P7/////////////////////////
//////////////////////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S
0fj/0tH4/+7u/P/////////////////////////////////////////////////////////////////+/v//9PP9/+Pj+//Z2Pn/
1NP4/9PS+P/S0fj/09L4/9XU+P/c2/n/6en8//j4/v//////////////////////////////////////////////////////////
//39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////////////////
//////////////////////////////z8/v/n5/v/1dT5/9HQ+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/R0Pj/0tH4/9nY+f/t
7Pz//v7///////////////////////////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/
0tH4/9LR+P/S0fj/0tH4/+7u/P///////////////////////////////////////////////////////Pz//+Pj+//S0fj/0tH4
/9LR+P/S0fj/0dD4/9LR+P/S0fj/0tH4/9LQ+P/S0fj/0tH4/9LR+P/U0/j/6ej8//7+////////////////////////////////
//////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////
////////////////////////////////////6un8/9LR+P/S0fj/0tH4/9LR+P/T0vj/3t76/+rq/P/t7fz/6Oj8/9zb+v/S0fj/
0tH4/9LR+P/S0fj/1NP4/+/v/P////////////////////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4
/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P/////////////////////////////////////////////////49/7/2Nf5/9LR
+P/S0fj/0tH4/9PS+P/n5vv//Pz///////////////////v7/v/m5fv/09L4/9LR+P/S0fj/0dD4/9zb+v/7+/7/////////////
//////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////
///////////////////////////////////////////t7Pz/0tH4/9LR+P/S0fj/0tH4/+Df+v/8/P//////////////////////
///////7+/7/3dz6/9LQ+P/S0fj/0tH4/9TT+P/y8v3///////////////////////////////////////39///f3/r/0dD4/9LR
+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P/////////////////////////////////////////////////j
4/v/0dD4/9LR+P/S0fj/09L4/+7u/P//////////////////////////////////////6un8/9LR+P/S0fj/0tH4/9LR+P/p6Pv/
//////////////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4
/+7u/P////////////////////////////////////////////7+///g3/r/0dD4/9LR+P/S0fj/1NP4//Pz/f//////////////
////////////////////////8O/9/9PS+P/S0fj/0tH4/9HQ+P/n5/v///////////////////////////////////////39///f
3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////////////////////////
//////7+///h4fr/0dD4/9LR+P/S0fj/1NP4//Ly/f//////////////////////////////////////7u38/9LR+P/S0fj/0tH4
/9LQ+P/n5/v///////////////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR
+P/S0fj/0tH4/+7u/P/////////////////////////////////////////////////p6Pv/0tH4/9LR+P/S0fj/0tH4/+vr/P//
///////////////////////////////+/v//5OT7/9LR+P/S0fj/0tH4/9LR+P/t7Pz/////////////////////////////////
//////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////////////
///////////////////////19f3/1tX5/9LR+P/S0fj/0tH4/9rZ+f/19f3////////////////////////////x8f3/1tX5/9LR
+P/S0fj/0tH4/9jX+f/4+P7///////////////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S
0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P/////////////////////////////////////////////////+/v//5ub7/9LR+P/S0fj/
0tH4/9LR+P/Y1/n/6Of7//Pz/f/29v7/8/P9/+fn+//X1vn/0tH4/9LR+P/S0fj/09L4/+rq/P//////////////////////////
//////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////
////////////////////////////////////////+/v+/+Xk+//U0/j/0tH4/9LR+P/S0fj/0tH4/9TT+P/V1Pj/1NP4/9LR+P/S
0fj/0tH4/9LR+P/U0/j/6Of7//39//////////////////////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/
0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////////////////////////////////////////////
//39///t7Pz/1dT5/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9bW+f/u7vz//v7/////////////////////
//////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//
//////////////////////////////////////////////////////////r6/v/j4vv/09L4/9LR+P/S0fj/0tH4/9PS+P/V1Pj/
09L4/9LR+P/S0fj/0tH4/9TT+P/l5Pv//Pz///////////////////////////////////////////////////39///f3/r/0dD4
/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////////////////////////////////
/////////f3//+Pi+//S0fj/0tH4/9LR+P/S0fj/4N/6//Hw/f/39/7/7+/8/9/e+v/S0fj/0tH4/9LR+P/S0fj/5uX7//7+////
//////////////////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/
0tH4/+7u/P//////////////////////////////////////////////////////8PD9/9TT+P/S0fj/0tH4/9LR+P/f3vr/+vr+
//////////////////v7/v/f3vr/0tH4/9LR+P/S0fj/1dT4//Pz/f////////////////////////////////////////////39
///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////////////////////
///////////////+/v//4+L7/9HQ+P/S0fj/0tH4/9TT+P/x8f3////////////////////////////v7/z/09L4/9LR+P/S0fj/
0dD4/+Xl+/////////////////////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4
/9LR+P/S0fj/0tH4/+7u/P/////////////////////////////////////////////////8/P//3Nv6/9HQ+P/S0fj/0tH4/9bV
+f/39/7////////////////////////////09P3/1dT4/9LR+P/S0fj/0dD4/+Df+v/+/v//////////////////////////////
//////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////////
///////////////////////////8+/7/29r5/9HQ+P/S0fj/0tH4/9bV+f/39/7////////////////////////////z8/3/1NP4
/9LR+P/S0fj/0dD4/+Df+v/+/v////////////////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR
+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P/////////////////////////////////////////////////+/f//4N/6/9HQ+P/S
0fj/0tH4/9TT+P/x8P3////////////////////////////r6vz/0tH4/9LR+P/S0fj/0dD4/+Pi+///////////////////////
//////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////
////////////////////////////////////////////6+v8/9LR+P/S0fj/0tH4/9LR+P/c2/n/9fT9//39///+/v///Pz///Dw
/f/X1vn/0tH4/9LR+P/S0fj/09L4/+7u/P////////////////////////////////////////////39///f3/r/0dD4/9LR+P/S
0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////////////////////////////////////////
+vr+/9va+f/R0Pj/0tH4/9LR+P/S0fj/1tX5/97d+v/h4Pr/3dz6/9XU+P/S0fj/0tH4/9LR+P/R0Pj/3t36//v7/v//////////
//////////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u
/P////////////////////////////////////////////////////////////Ly/f/X1vn/0dD4/9LR+P/S0fj/0tH4/9HQ+P/R
0Pj/0dD4/9LR+P/S0fj/0tH4/9LR+P/b2vn/9vb+//////////////////////////////////////////////////39///f3/r/
0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////////////////////////////
///////////////////////z8v3/3Nv6/9PS+P/R0Pj/0tD4/9LR+P/S0fj/0tH4/9HQ+P/R0Pj/1dT5/+Pj+//39/7/////////
//////////////////////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S
0fj/0tH4/+7u/P//////////////////////////////////////////////////////////////////////+vr+/+3s/P/h4Pr/
2tn5/9fW+f/X1vn/2Nf5/93c+v/m5fv/9PT9//7+////////////////////////////////////////////////////////////
//39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////////////////
///////////////////////////////////////////////////+/v//+/v+//j4/v/4+P7/+fn+//z8////////////////////
//////////////////////////////////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/
0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4
/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7u/P//////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////39///f3/r/0dD4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/+7t/P//////
/v7///7+///+/v///v7///7+///+/v///v7///7+///+/v///v7///7+///+/v///v7///7+///+/v///v7///7+///+/v///v7/
//7+///+/v///v7///7+///+/v///v7///7+///+/v///v7///7+///+/v///v7///7+///+/v///v7///39///f3/r/0dD4/9LR
+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9zc+v/j4vr/4uL6/+Li+v/i4vr/4uL6/+Li+v/i4vr/4uL6/+Li+v/i
4vr/4uL6/+Li+v/i4vr/4uL6/+Li+v/i4vr/4uL6/+Li+v/i4vr/4uL6/+Li+v/i4vr/4uL6/+Li+v/i4vr/4uL6/+Li+v/i4vr/
4uL6/+Li+v/i4vr/4uL6/+Li+v/i4vr/4uL6/+Lh+v/X1vn/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4
/9LR+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ
+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/R0Pj/0dD4/9HQ+P/S
0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/
0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4
/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR
+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S
0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/
0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4
/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR
+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P/S0fj/0tH4/9LR+P8A
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAoAAAAeAAAAOoAAAABAAgAAAAAANg2AACHHQAAhx0AAAABAAAAAQAA0tH4AOTj+wDu7vwA////AO/v/QDr6/wA4N/6
AOLh+gD5+f4A9PP9ANva+QDY1/kA3t76AN3c+gDW1fkA5eT7ANTT+ADa2fkA6Of7AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAABAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIC
AgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDBAUGBgYGBg8FCQMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMEBhEAAAAAAAAAAAAAABAKDwgDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMIBw4A
AAAAAAAAAAAAAAAAAAAAAAAKBQMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwYQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4PAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMFDgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEQQDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwYAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAGAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMIDQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADQgDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMRAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsIAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAw0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDDwAAAAAAAAAAAAAAAAAAAAsGEgUFDwwLAAAAAAAAAAAAAAAAAAAABwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMIEAAAAAAAAAAAAAAAAAARBAMDAwMDAwMDBA0A
AAAAAAAAAAAAAAAAAAkDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMNAAAAAAAAAAAAAAAAAA8DAwMDAwMDAwMDAwMFEAAAAAAAAAAAAAAAABEDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwkAAAAAAAAAAAAAAAAA
DwMDAwMDAwMDAwMDAwMDCAsAAAAAAAAAAAAAAAAEAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwYAAAAAAAAAAAAAAAAHAwMDAwMDAwMDAwMDAwMDAwQQAAAAAAAAAAAAAAAN
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwsAAAAAAAAAAAAAABEDAwMDAwMDAwMDAwMDAwMDAwMGAAAAAAAAAAAAAAAQAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDCQAAAAAAAAAAAAAAAAUDAwMDAwMDAwMDAwMDAwMD
AwMIEAAAAAAAAAAAAAAABQMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDEgAAAAAAAAAAAAAADgMDAwMDAwMDAwMDAwMDAwMDAwMDDQAAAAAAAAAAAAAABgMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDBgAAAAAAAAAAAAAADQMD
AwMDAwMDAwMDAwMDAwMDAwMDDwAAAAAAAAAAAAAACgMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDDAAAAAAAAAAAAAAABgMDAwMDAwMDAwMDAwMDAwMDAwMDBQAAAAAAAAAAAAAA
EQMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
EQAAAAAAAAAAAAAABQMDAwMDAwMDAwMDAwMDAwMDAwMDBAAAAAAAAAAAAAAAEQMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDEQAAAAAAAAAAAAAABQMDAwMDAwMDAwMDAwMDAwMD
AwMDAwAAAAAAAAAAAAAAEQMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDDQAAAAAAAAAAAAAABQMDAwMDAwMDAwMDAwMDAwMDAwMDBQAAAAAAAAAAAAAAEQMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDBgAAAAAAAAAAAAAABwMD
AwMDAwMDAwMDAwMDAwMDAwMDBQAAAAAAAAAAAAAAEQMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDEgAAAAAAAAAAAAAADQMDAwMDAwMDAwMDAwMDAwMDAwMDDAAAAAAAAAAAAAAA
DAMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
CQAAAAAAAAAAAAAADgMDAwMDAwMDAwMDAwMDAwMDAwMDDgAAAAAAAAAAAAAAEgMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwsAAAAAAAAAAAAAAA8DAwMDAwMDAwMDAwMDAwMD
AwMPAAAAAAAAAAAAAAAACAMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAw8AAAAAAAAAAAAAABAJAwMDAwMDAwMDAwMDAwMDAwkQAAAAAAAAAAAAAAANAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMOAAAAAAAAAAAAAAAL
CQMDAwMDAwMDAwMDAwMDCAsAAAAAAAAAAAAAAAAJAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMSAAAAAAAAAAAAAAAAEA8DAwMDAwMDAwMDAwMFDgAAAAAAAAAAAAAAAAwD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDCgAAAAAAAAAAAAAAAAAOBgQDAwMDAwMIEhEAAAAAAAAAAAAAAAAACwgDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDCAsAAAAAAAAAAAAAAAAAAAAAEREREQ4AAAAA
AAAAAAAAAAAAAAAQCAMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwgKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsJAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDBxAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACggDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwkRAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4SAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDBQ4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQBwgDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMICgAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAEQQDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwQOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAPAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDBBAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMEEAAAAAAAAAAAAAAAABEPCQMDCBIKAAAAAAAAAAAAAAAAAA8DAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwgOAAAAAAAAAAAAAAAQBQMDAwMDAwMDCREAAAAAAAAAAAAAAAAFAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwwAAAAAAAAAAAAAABAEAwMDAwMDAwMDAwMN
AAAAAAAAAAAAAAAOAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDCQAAAAAAAAAAAAAAAAUDAwMDAwMDAwMDAwMDEQAAAAAAAAAAAAAADwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDDAAAAAAAAAAAAAAA
DAMDAwMDAwMDAwMDAwMDCQAAAAAAAAAAAAAADgMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDDgAAAAAAAAAAAAAACQMDAwMDAwMDAwMDAwMDAwoAAAAAAAAAAAAAAAQD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMEAAAAAAAAAAAAAAARAwMDAwMDAwMDAwMDAwMDAwcAAAAAAAAAAAAAAAYDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMPAAAAAAAAAAAAAAAMAwMDAwMDAwMDAwMDAwMD
AwUAAAAAAAAAAAAAAAoDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMGAAAAAAAAAAAAAAAGAwMDAwMDAwMDAwMDAwMDAwUAAAAAAAAAAAAAABEDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMGAAAAAAAAAAAAAAAG
AwMDAwMDAwMDAwMDAwMDAwUAAAAAAAAAAAAAABEDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMGAAAAAAAAAAAAAAAGAwMDAwMDAwMDAwMDAwMDAwUAAAAAAAAAAAAAABED
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMGAAAAAAAAAAAAAAAGAwMDAwMDAwMDAwMDAwMDAw8AAAAAAAAAAAAAABEDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMPAAAAAAAAAAAAAAARAwMDAwMDAwMDAwMDAwMD
Aw0AAAAAAAAAAAAAAA0DAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMJAAAAAAAAAAAAAAAACQMDAwMDAwMDAwMDAwMDCBAAAAAAAAAAAAAAAAcDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDDgAAAAAAAAAAAAAA
CgMDAwMDAwMDAwMDAwMDCgAAAAAAAAAAAAAAAAQDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDBgAAAAAAAAAAAAAAAAcDAwMDAwMDAwMDAwMNAAAAAAAAAAAAAAAADgMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDCQAAAAAAAAAAAAAAAAAKCQMDAwMDAwMDCQoAAAAAAAAAAAAAAAAADwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwYAAAAAAAAAAAAAAAAAABEHBQUFBQcKAAAA
AAAAAAAAAAAAAAAOAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwgOAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMEEAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA8DAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDDwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAw8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAPAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMFEAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAACwQDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDCA0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4PAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMFDQAA
AAAAAAAAAAAAAAAAAAAAAAAODwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwkHCgAAAAAAAAAAAAAAAAALDAQDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMEBQYGBgYGBgYHBQgDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAwMDAwMDAwMD
AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD
AwMDAwMDAwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIC
AgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgEAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==
'''
icondata = base64.b64decode(icon)

# --- MAIN WINDOW --- #

root = Tk()
root.title(PROGRAM_TITLE + ' - 러블리즈 갤러리 (초코맛제티)')
iconFile = 'icon.tmp'
with open(iconFile, 'wb') as f:
    f.write(icondata)
root.iconbitmap(iconFile)
os.remove(iconFile)

# --- IMPORT SETTINGS --- #

keyword_list = []
destination_folder = StringVar()
create_indiv_dir = BooleanVar()
defaultLU = datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0)
last_update = defaultLU
import_settings()

# --- DEFINE GLOBAL VARIABLE --- #

continue_download = BooleanVar()  # 다운로드 진행 여부
continue_download.set(True)

# --- MENU BAR --- #
menubar = Menu(root)

filemenu = Menu(menubar, tearoff=0)
filemenu.add_command(label='작업 목록 불러오기', command=load_list_btn)
filemenu.add_command(label='현재 작업 목록 저장하기', command=save_list_btn)
filemenu.add_separator()
filemenu.add_command(label='설정', command=modify_settings_btn)
filemenu.add_separator()
filemenu.add_command(label='닫기', command=lambda: root.destroy())
menubar.add_cascade(label='파일', menu=filemenu)

helpmenu = Menu(menubar, tearoff=0)
helpmenu.add_command(label='도움말 보기', command=lambda: webbrowser.open_new(HELP_LINK))
helpmenu.add_separator()
helpmenu.add_command(label='업데이트 확인', command=check_update)
helpmenu.add_command(label=PROGRAM_TITLE+' 정보', command=show_info)
menubar.add_cascade(label='도움말', menu=helpmenu)

root.config(menu=menubar)

# BUTTONS

treeOpsFrame = ttk.Frame()
treeOpsFrame.pack(pady=GUI_PARAM['FramePadY'], fill=BOTH)

# LEFT BUTTONS
treeAddDelFrame = ttk.Frame(treeOpsFrame)
treeAddDelFrame.pack(side=LEFT, in_=treeOpsFrame)

ManualAdd = ttk.Button(text='개별 주소 추가', command=manual_add_btn)
ManualAdd.grid(column=0, row=0, padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'],
               in_=treeAddDelFrame, sticky=N+S+E+W)

batch_add = ttk.Button(text='사이트 일괄 추가', command=batch_add_btn)
batch_add.grid(column=1, row=0, padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'],
               in_=treeAddDelFrame, sticky=N + S + E + W)

delete_item = ttk.Button(text='삭제', command=delete_item_btn)
delete_item.grid(column=2, row=0, padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'],
                 in_=treeAddDelFrame, sticky=N + S + E + W)

clean_item = ttk.Button(text='완료 내역 정리', command=clean_item_btn)
clean_item.grid(column=3, row=0, padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'],
                in_=treeAddDelFrame, sticky=N + S + E + W)

# RIGHT BUTTONS
treeMainOpsFrame = ttk.Frame(treeOpsFrame)
treeMainOpsFrame.pack(side=RIGHT, in_=treeOpsFrame)

execution_label = StringVar()
execution_label.set('실행')
execution = ttk.Button(textvariable=execution_label, command=download_items)
execution.pack(padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'], in_=treeMainOpsFrame, side=RIGHT)

check_duplicates = ttk.Button(text='중복이면말좀해주지', command=check_duplicate)
check_duplicates.pack(padx=GUI_PARAM['ButtonPadX'], pady=GUI_PARAM['ButtonPadY'], in_=treeMainOpsFrame, side=RIGHT)

# --- TREE --- #

# TREE-RELATED PARAMETERS
tree_column_label = ('', '주소', '제목', '전체 크기', '진행상황')
tree_column_align = ('center', 'w', 'center', 'center', 'center', 'center')
tree_column_width = (20, 200, 200, 120, 120)
tree_column_stretch = (False, True, True, False, False)
tree_column_num = len(tree_column_label)
tree_column_id = ['#' + str(i + 1) for i in range(tree_column_num - 1)]

# GENERATE CONTAINER
container = ttk.Frame(borderwidth=1, relief=SUNKEN)
container.pack(fill=BOTH, expand=1)

# GENERATE TREE
tree = ttk.Treeview(container, columns=tree_column_id, displaycolumns='#all', takefocus=True, selectmode='extended')

# GENERATE SCROLLBAR
vsb = ttk.Scrollbar(orient="vertical", command=tree.yview)
hsb = ttk.Scrollbar(orient="horizontal", command=tree.xview)
tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

# POSITION TREE
tree.grid(column=0, row=0, sticky=N+S+E+W, in_=container)
vsb.grid(column=1, row=0, in_=container, sticky=N+S)
hsb.grid(column=0, row=1, in_=container, sticky=E+W)

# CONFIGURE TREE
container.grid_rowconfigure(0, weight=1)  # row = 0: position of tree -> equivalently expand
container.grid_columnconfigure(0, weight=1)  # column = 0: position of tree -> equivalently expand
for i in range(tree_column_num):
    tree.heading('#' + str(i), text=tree_column_label[i])
for i in range(tree_column_num):
    tree.column('#' + str(i), anchor=tree_column_align[i], width=tree_column_width[i], minwidth=tree_column_width[i],
                stretch=tree_column_stretch[i])

# --- IMAGE --- #
# 하단 배너 base64
photoraw = '''

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
5hYRSNYHayyt3mOtXucbX3yOrz36JFNVFysEI2uptebO2j3OXL/EB2dOc+b0JxzavpPvvfB7bJ2dpyzLdH7PI7vwBYcBZ00x1udl
EC1SbazNt4cr4GqS4hQtMgRTjT8XDGBdcWZXn8h5qUJtumbUp6kHzvtSlM4oUJZuT0UrT0bX/BYXJnhsSpYx3FpbYqQsc71J5rol
5RCkrt1IPDEU1ntCrGLQaO7aIaZTsJsuylj6Tc1qM6QjFB3lEscoTEwDL4RFWYlAcXMw4Fbh0tt3kMyXPeboUpkBGO3gpTXaND6R
FG0LfrA04fay8aH7DmIuSVUBVLLgTj3iRj1gvjvJlrJADPuY0RA9HKBDPSapKKsOYqIHouLK2iqjAu7rVExMTjhlpnahXbbRaCVR
RYWUJZ3eFJ3JKZbMiBtmDWklHSOoJwrmZieY7neojHYKhnDJOTqdiu7EJBPTc6xruKj7zFQ9tqsuhVDcGa5zVQ7ZJrtMl1WrThU4
A1JZdpBVxa21NZalYbrbY0c1RaEtt+p1zut1pqVidzFBYS1aG4zUoEnyoxM62FhcPvEEiTs/VqgCVVZoJbkzWme9lC4BF4Lpqsuc
7FIM3b60xqA9zZVCuHNPRcFqPWJgNaNCUCsoNfSkoNfrUgrrC/m6ERRlSafTQxVdbgrNmhq6ep0G5sqKuc4kRV+57aOdMgeuxmc4
G1tUXcpqgjUBq6ZhqlMxqQo3O+ujE4wOBMgpfGVF1elRdifoC7hV91mzDb1Oh62dCZQ13sPTxJILhSooiy6NLLjbNFAWzHR6SKW4
OVxntRkwYyXTZQdltMNtnfDZKZuuDVn2uCkNtWmYrzpUUmEHxP1sfC744AUry4qqmqSqJlhSlmv1Oo01zBcd5js9CiswukZaHevf
CSGcx63ssmQty4ycB9o7BXpWsLWokGpEU48cVdpEpk5xR4kORxrnZcRczxFZA0HvaWUltxEl4+/5nrdAkTS50EqUmFtMLihTeTyh
E/iCcCh8hyHchrErl77SrSBsj829LZ/H/iMc2oLEBh4oCEkdWtlOxoXP7PlkFctjw92nGMfs3wtDM8ZQO78wCEkBKOE+I3FhejEc
LKzU+FkNx0ykBWUsxWgEyyuOFFiLtAZrtUsHagVWlQjlCns6eBh/wNd6N70PFWoMSkka4zZx2amQnRKrinborfdMBQUnWrcd9NzB
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
2XN48swpOEQEP4K9z+ufFSA6ZxVgKTgPyje0YklkmwQpCQk+jiNMN1OwnHxzZL7LzSYrYHYYjYGPATYyvI9itm1dTjchFgDNolDg
FDR5rYK1TCXKgSCstRq0rPC7dEvsx1G+zyG0ZT3GmIIkqH9uED8b13eAtWqyqTxH81CRc6LpsE7Wut7ui7mgVzAr+ZXmOw5+9JK7
qe8QQ8A4DPDDEpRMzgIQwwggVoll5S8HjxgE1Nq+h2WH4EcVkKR9DoQYCTAWxjgQVDAzRTNM1opFwzhiNXpQ72C6Hn3Xa4h4oOtm
6nszYlwthcYxQkLCa24oxBw0hEBAFP+ukKP5aa4uBrwPjVkhiyo58/Z0IWWtRTd3WA0efjVKJDnladbYzMTIWPR9j3EQE1prRGAD
SKPVMVi1Yt6PSH5vYwgAGbiuh+17XLxxHcs44uj8MO45fgrD9VuwIJy/fhUXV3s4Od/S9ZVXkfJAGUvjVK9nSRbuY8TpkycxvvdL
XF3eyH4/BSDJW6s0IAAPnT6L48dPIN64Dq4PyZrHksyl7TsJod91SicJSBKGQTRzae3nc7Wc8bkL+s+Q5Bn7+MMP8c1Xf4g9eAAE
RxYwwKj+6BYGhgWDBWLYCDz70Gdw9gvPoYOYw46rEZJsGuIPxgBbnZMkYIMwtw53nziBew+fBIUglywM0SBm1wquiM86nJj9UGtN
lL5RQargl4p9lPeq8KixaArBX85/VJH9JuZ5VV21GV95lStXac6062SDpqdCj6hPWNLyZQ3oOPO4CmrZ5CPeCnZr6DaPf21spbuy
dlQZk6CK9KPW6jUoLFMrvc9aMJJUR6WwlshgvSZIDRqRBBwUwuSJ4Qy4ypgqZFOPjKvv1ntcva92Sq67Asp3rIMaMMx1X9IYlZHV
JolNOZQJTod6apDUlrhd1JNp2zCheQJ0M4UYQSHAeK/28jHbPpPmpKjheJ5kXQE5KS7VJoBU5ouht+jIY5kuzwxYtOymBZgfSuuk
2ShrtZV5uWN8dN48ddyKF9y8qRbihtZbHcm064lxITOoZkB1aVagwoXhJB4I1IyudKvuYrq90MLapbT9qmZabtSMivKjxdcn/dhQ
qLpZZO1busmGjsFo/Q3HbChTWi3mTKjmTpkgpTa0rEbomZKvbB/5sc2R1pLlji9CPozqLnP+ccLgamae2cNkPNUop5Qo/K38zkD2
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
'''

# 현재 배너 비활성화 상태

# photodata=base64.b64decode(photoraw)
# photo = PhotoImage(data = photodata)
# label = ttk.Label(image = photo)
# label.image = photo
# label.pack()

# --- STATUS BAR --- #
# 최하단 상태표시줄

status_frame = ttk.Frame(borderwidth=0.5, relief=FLAT)
status_frame.pack(fill=X, side=BOTTOM)

working_status_str_1 = StringVar()
working_status_str_1.set('')

working_status_str_2 = StringVar()
working_status_str_2.set('')

ttk.Label(textvariable=working_status_str_1, anchor=W).pack(side=LEFT, in_=status_frame)
ttk.Label(textvariable=working_status_str_2, anchor=E).pack(side=LEFT, in_=status_frame)


# --- TERMINATION --- #
check_update(False)  # check the update status after startup (esp in case of the first startup)
root.mainloop()
