#!/usr/bin/env python3
import os
import shutil
import subprocess
import urllib.request
from zipfile import ZipFile
import time
import sys


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

def run_cmd(cmd):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    status = process.wait()
    if status != 0:
        Logger().fatal_error('Error executing "{}": error code {}'.format(cmd, status))

    return process.communicate()[0]


def init_git_repository():
    Logger().log('Initializing empty git repository...')
    run_cmd('git init')
    with open('.gitignore', 'w') as f:
        f.write('sharelatex-git.py\n')
        f.write('sharelatex-git\n')
        f.write('.idea/*')
    f.close()

def is_git_repository():
    dir = '.git'
    os.path.exists(dir) and os.path.isdir(dir)

def ensure_git_repository_started():
    if not is_git_repository():
        init_git_repository()

def commit_all_changes(message):
    run_cmd('git add -A')
    run_cmd('git commit -m"[sharelatex-git-integration {}] {}"'.format(get_timestamp(),message))

def files_changed():
    out = run_cmd('git status .').decode('utf-8')
    return 'nothing to commit, working directory clean' not in out.lower()

def fetch_updates(sharelatex_id, skip_LaTeX_folder=False):
    file_name = 'sharelatex.zip'
    final_url = "https://www.sharelatex.com/project/{}/download/zip".format(sharelatex_id)

    Logger().log("Downloading files from {}...".format(final_url))
    urllib.request.urlretrieve(final_url, file_name)
    Logger().log("Decompressing files...")
    with ZipFile(file_name, 'r') as f:
        f.extractall()
    os.remove(file_name)

    if skip_LaTeX_folder:
        Logger().log("Moving files out of LaTeX folder")
        for filename in os.listdir('LaTeX'):
            shutil.move(os.path.join('LaTeX', filename), '.')
        os.rmdir('LaTeX')

def go():
    ensure_git_repository_started()
    fetch_updates('test_id', False)

    if files_changed():
        message = 'Adding files test'
        Logger().log('Comitting changes. Message: {}'.format(message))
        commit_all_changes(message)
    else:
        Logger().log('No changes to commit.')
    Logger().log('All done!')

go()