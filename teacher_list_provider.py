import os
import re
import json
import hashlib
import requests
import datetime

from github import Github
from apscheduler.schedulers.blocking import BlockingScheduler
from time import sleep

#from dotenv import load_dotenv


lk_url = 'https://e.mospolytech.ru/old?p=rasp'
lk_url_auth = 'https://e.mospolytech.ru/old'
teacher_schedule = 'https://kaf.dmami.ru/lessons/teacher-html?id='
teacher_schedule_referer = 'https://kaf.dmami.ru'
github_repo = 'mospolyhelper/up-to-date-information'
github_file = 'teacher_ids.json'

def get_session_id(login: str, password: str):
    headers = {
        'referer': lk_url_auth
    }
    data = {
        'ulogin' : login,
        'upassword' : password,
        'login_as' : 'staff',
        'auth_action' : 'userlogin'
    }
    session = requests.Session()
    session.post(url=lk_url_auth, data=data, headers=headers)
    return session

def get_lk_html(session):
    headers = {
        'referer' : lk_url
    }
    return session.get(url=lk_url, headers=headers).text

def get_teacher_map(html: str):
    # <option value='1234'>Арсентьев Дмитрий Андреевич</option>
    # <option value='(.*?)'>(.*?)<\/option>
    matches = dict(re.findall("<option value='(.*?)'>(.*?)<\\/option>", html))
    if ('0' in matches):
        del matches['0']
    return matches

def get_max_id(teacher_map: dict):
    max_id = -1
    for key in teacher_map:
        parsed = int(key)
        if (parsed > max_id):
            max_id = parsed
    return max_id

def append_teacher_map(teacher_map: dict, from_id: int):
    id = from_id
    fails = 0
    regex = '<h3 class="teacher-info__name">(.*?)<\\/h3>'
    regex_end = '<img.*?>'
    #regex_kaf = '<span class="label alert-info">(.*?)<\\/span>'
    headers = {
        'referer': teacher_schedule_referer
    }
    while (True):
        if (fails > 500):
            return
        # to slow down
        sleep(0.5)
        html = try_get(teacher_map, id, headers)

        if len(re.findall(regex_end, html)) != 0:
            print('Not found page for id: ' + str(id))
            return

        matches = re.findall(regex, html)

        if len(matches) == 0:
            print('Schedule is empty for id: ' + str(id))
            id += 1
            fails += 1
            continue

        print('Successfully found for id: ' + str(id) + matches[0])
        teacher_map[str(id)] = matches[0]
        id += 1
        fails = 0

def try_get(teacher_map: dict, id: int, headers):
    i = 1
    while True:
        try:
            html = requests.get(teacher_schedule + str(id), headers=headers)
            return html.text
        except Exception as e:
            print('Get id request exception: ' + repr(e))
            if i >= 64:
                return ''
            sleep(i)
            i *= 2
            continue
        


def upload_list_to_github(github_token: str, teacher_map: dict):
    text = json.dumps(teacher_map, ensure_ascii=False)
    text_bytes = text.encode('utf-8')

    sha = hashlib.sha1()
    sha.update(text_bytes)

    g = Github(github_token)
    repo = g.get_repo(github_repo)
    contents = repo.get_contents(github_file, ref="master")
    repo.update_file(contents.path, "Autoupdate", text, contents.sha, branch="master")

def launch():
    print('Started')
    login = os.environ['LK_LOGIN']
    password = os.environ['LK_PASSWORD']
    session = get_session_id(login, password)
    html = get_lk_html(session)
    print('Downloaded HTML with teacher list')

    teacher_map = get_teacher_map(html)
    print('Teacher list parsed')
    max_id = get_max_id(teacher_map)
    print('Max id of teacher list from the https://e.mospolytech.ru/?p=rasp is ' + str(max_id))
    append_teacher_map(teacher_map, max_id + 1)
    print('Teacher list appended by continuous parsing of ids')

    github_token = os.environ['GH_TOKEN']
    upload_list_to_github(github_token, teacher_map)
    print('Uploaded to github')
    print('Updated')


if (__name__ == '__main__'):
    #load_dotenv(dotenv_path='var.env')
    #launch()
    sched = BlockingScheduler()
    sched.add_job(launch, 'interval', days=2, next_run_time=datetime.datetime.now())
    sched.start()

