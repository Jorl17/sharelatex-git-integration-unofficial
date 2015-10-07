#!/usr/bin/env python3
from optparse import OptionParser
import os
import shutil
import subprocess
import urllib.request
from zipfile import ZipFile
import time
import sys
import urllib.parse
import re


def get_timestamp():
    return time.strftime('%Y/%m/%d %H:%M:%S')

class Logger:

    shell_mod = {
        '':'',
       'PURPLE' : '\033[95m',
       'CYAN' : '\033[96m',
       'DARKCYAN' : '\033[36m',
       'BLUE' : '\033[94m',
       'GREEN' : '\033[92m',
       'YELLOW' : '\033[93m',
       'RED' : '\033[91m',
       'BOLD' : '\033[1m',
       'UNDERLINE' : '\033[4m',
       'RESET' : '\033[0m'
    }

    def log ( self, message, is_bold=False, color='', log_time=True, indentation_level=0):
        prefix = ''
        suffix = ''

        if log_time:
            prefix += '[{:s}] {:s}'.format(get_timestamp(), '...'*indentation_level)

        if os.name.lower() == 'posix':
            if is_bold:
                prefix += self.shell_mod['BOLD']
            prefix += self.shell_mod[color.upper()]

            suffix = self.shell_mod['RESET']

        message = prefix + message + suffix
        try:
            print ( message )
        except:
            print ("Windows can't display this message.")
        sys.stdout.flush()


    def error(self, err, log_time=True, indentation_level=0):
        self.log(err, True, 'RED', log_time, indentation_level)

    def fatal_error(self, err, log_time=True, indentation_level=0):
        self.error(err, log_time, indentation_level)
        exit()

def run_cmd(cmd, allow_fail=False):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    status = process.wait()
    if not allow_fail and status != 0:
            Logger().fatal_error('Error executing "{}": error code {}'.format(cmd, status))

    return process.communicate()[0]


def init_git_repository():
    Logger().log('Initializing empty git repository...')
    run_cmd('git init')

def get_base_git_root():
    return run_cmd('git rev-parse --show-toplevel').decode('utf-8').strip()

def get_git_ignore():
    git_base = get_base_git_root()
    return os.path.join(git_base, '.gitignore')

def ensure_gitignore_is_fine():
    git_ignore = get_git_ignore()
    try:
        with open(git_ignore, 'r') as f:
            lines=[line.strip() for line in f.readlines()]
    except:
        lines = []

    try:
        with open(git_ignore, 'a') as f:
            def write_if_not_there(s):
                if s not in lines:
                    f.write(s + '\n')

            write_if_not_there('sharelatex-git.py')
            write_if_not_there('sharelatex-git')
            write_if_not_there('.sharelatex-git')
    except:
        Logger().log("Can't edit .gitignore file [{}].".format(git_ignore), True, 'YELLOW')


def is_git_repository():
    status = run_cmd('git status', True).decode('utf-8')
    return 'not a git repository' not in status.lower()

def ensure_git_repository_started():
    if not is_git_repository():
        init_git_repository()

def commit_all_changes(message):
    run_cmd('git add -A .')
    run_cmd('git add -A {}'.format(get_git_ignore()))
    if message:
        run_cmd('git commit -m"[sharelatex-git-integration {}] {}"'.format(get_timestamp(),message))
    else:
        run_cmd('git commit -m"[sharelatex-git-integration {}]"'.format(get_timestamp()))

def files_changed():
    out = run_cmd('git status .').decode('utf-8')
    return 'nothing to commit, working directory clean' not in out.lower()

def fetch_updates(sharelatex_id, skip_LaTeX_folder=True):
    file_name = 'sharelatex.zip'
    final_url = "https://www.sharelatex.com/project/{}/download/zip".format(sharelatex_id)

    Logger().log("Downloading files from {}...".format(final_url))
    urllib.request.urlretrieve(final_url, file_name)
    Logger().log("Decompressing files...")
    with ZipFile(file_name, 'r') as f:
        f.extractall()
    os.remove(file_name)

    if skip_LaTeX_folder:
        Logger().log("Moving files out of LaTeX folder...")
        for filename in os.listdir('LaTeX'):
            shutil.move(os.path.join('LaTeX', filename), '.')
        os.rmdir('LaTeX')

def read_saved_sharelatex_document():
    doc = '.sharelatex-git'

    try:
        with open(doc, 'r') as f:
            return f.readline().strip()
    except:
        return None

def write_saved_sharelatex_document(id):
    doc = '.sharelatex-git'

    try:
        with open(doc, 'w') as f:
            f.write('{}\n'.format(id))
    except:
        Logger().log("Problem creating .sharelatex-git file", True, 'YELLOW')

def determine_id(id):
    saved_id = read_saved_sharelatex_document()
    if id and saved_id:
        if id != saved_id:
            while True:
                print(
                    'Conflicting ids. Given {old}, but previous records show {new}. Which to use?\n1. {old} [old]\n2. {new} [new]'.format(
                        old=saved_id, new=id))
                ans = input('Id to use [blank = 2.] -> ')
                if ans.strip() == '':
                    ans = '2'
                if ans.strip() == '1' or ans.strip() == '2':
                    break
            id = saved_id if int(ans.strip()) == 1 else id
    elif not saved_id and not id:
        Logger().fatal_error('No id supplied! See (-h) for usage.')
    elif saved_id:
        id = saved_id

    return id

def git_push():
    Logger().log(
        'Pushing is an experimental feature. If you experience lockdowns, hit CTRL+C. It means you probably have not configured password aching and/or passwordless pushes.',
        True, 'YELLOW')
    run_cmd('git push origin master')


def go(id, message, push):
    id = determine_id(id)

    ensure_git_repository_started()
    ensure_gitignore_is_fine()
    fetch_updates(id, False)

    if files_changed():
        if message:
            Logger().log('Comitting changes. Message: {}.'.format(message))
        else:
            Logger().log('Comitting changes. No message.')
        commit_all_changes(message)

        if push:
            git_push()
    else:
        Logger().log('No changes to commit.')

    write_saved_sharelatex_document(id)
    Logger().log('All done!')

def extract_id_from_input(i):
    if 'http:' or 'https:' in i.lower():
        try:
            path = urllib.parse.urlsplit(i).path
            p = re.compile("/project/([a-zA-Z0-9]*).*", re.IGNORECASE)
            return p.search(path).group(1)
        except:
            Logger().log('Unrecognized id supplied ({}) [http/https]'.format(i))
    else:
        p = re.compile("[a-zA-Z0-9]*")
        if p.match(i):
            return i
        else:
            Logger().log('Unrecognized id supplied ({})'.format(i))

def parse_input():
    parser = OptionParser("usage: %prog [options] [id].\n"
    "e.g.\n\t%prog -m 'Wrote Thesis introduction' https://www.sharelatex.com/project/56147712cc7f5d0adeadbeef\n"
    "\t%prog -m 'Wrote Thesis introduction' 56147712cc7f5d0adeadbeef\n"
    "\t%prog -m 'Wrote Thesis introduction'                                                            [id from last invocation is used]\n"
    "\t%prog                                                                                           [id from last invocation is used, nothing is added to commit message]")
    parser.add_option('-m', '--message', help='Commit message (default: "").', dest='message', type='string', default='')
    parser.add_option('-p', "--push", help="Push after doing commit (default: don't push) [EXPERIMENTAL]", dest='do_push', action='store_true',default=False)

    (options, args) = parser.parse_args()

    if len(args) == 1:
        id = extract_id_from_input(args[0])
    elif len(args) > 1:
        parser.error('Too many arguments.')
    else:
        id = None

    return id, options.message, options.do_push

go(*parse_input())