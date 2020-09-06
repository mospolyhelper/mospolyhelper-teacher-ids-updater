import os
import re
import json
import hashlib
import requests

from github import Github
from apscheduler.schedulers.blocking import BlockingScheduler


lk_url = 'https://e.mospolytech.ru/?p=rasp'
lk_url_auth = 'https://e.mospolytech.ru/index.php'
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
    print('Starting')
    login = os.environ['LK_LOGIN']
    password = os.environ['LK_PASSWORD']
    session = get_session_id(login, password)
    html = get_lk_html(session)
    
    teacher_map = get_teacher_map(html)

    github_token = os.environ['GH_TOKEN']
    upload_list_to_github(github_token, teacher_map)
    print('Updated')


if (__name__ == '__main__'):
    sched = BlockingScheduler()
    sched.add_job(launch, 'interval', days=1)

