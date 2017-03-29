#!/usr/bin/env python3
##
## Copyright (C) 2015 João Ricardo Lourenço <jorl17.8@gmail.com>
##
## Github: https://github.com/Jorl17
##
## Project main repository: https://github.com/Jorl17/sharelatex-git-integration-unofficial
##
## This file is part of sharelatex-git-integration-unofficial.
##
## sharelatex-git-integration-unofficial is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 2 of the License, or
## (at your option) any later version.
##
## sharelatex-git-integration-unofficial is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with sharelatex-git-integration-unofficial.  If not, see <http://www.gnu.org/licenses/>.
##
from optparse import OptionParser
from bs4 import BeautifulSoup
from zipfile import ZipFile, BadZipFile
import os
import shutil
import subprocess
import requests
import time
import sys
import re
import getpass
import configparser

#------------------------------------------------------------------------------
# Logger class, used to log messages. A special method can be used to
# shutdown the application with an error message.
#
# This is a modified version of what we used with
# https://github.com/xJota/NowCrawling
#------------------------------------------------------------------------------
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

#------------------------------------------------------------------------------
# Run a command and return its output. If there's a failure, crash and burn,
# but only if allow_fail = False.
#------------------------------------------------------------------------------
def run_cmd(cmd, allow_fail=False):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    status = process.wait()
    if not allow_fail and status != 0:
            Logger().fatal_error('Error executing "{}": error code {}. Output: {}'.format(cmd, status, process.communicate()[0]))

    return process.communicate()[0]

#------------------------------------------------------------------------------
# Initialize an empty git repository
#------------------------------------------------------------------------------
def init_git_repository():
    Logger().log('Initializing empty git repository...')
    run_cmd('git init')

#------------------------------------------------------------------------------
# Get the root of an existing GIT repository. Useful to find stuff like
# .gitignore
#------------------------------------------------------------------------------
def get_base_git_root():
    return run_cmd('git rev-parse --show-toplevel').decode('utf-8').strip()

#------------------------------------------------------------------------------
# Get the path to the .gitignore of this git repository
#------------------------------------------------------------------------------
def get_git_ignore():
    git_base = get_base_git_root()
    return os.path.join(git_base, '.gitignore')

#------------------------------------------------------------------------------
# Make sure that sharelatex-git's files are not added to project management,
# and that they're always present in the .gitignore.
#------------------------------------------------------------------------------
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

#------------------------------------------------------------------------------
# Checks if this directory is part of a git repository
#------------------------------------------------------------------------------
def is_git_repository():
    status = run_cmd('git status', True).decode('utf-8')
    return 'not a git repository' not in status.lower()

#------------------------------------------------------------------------------
# Make sure that we are in a git repository. It either already exists, or
# we create it.
#------------------------------------------------------------------------------
def ensure_git_repository_started():
    if not is_git_repository():
        init_git_repository()

#------------------------------------------------------------------------------
# Commit all changes. Note that we do this with '.' at the end of the command,
# so as to only commit changes in our directory. We also commit any possible
# changes to the gitignore file. The commit message is optional and it is
# always preceeded by a timestamp and the sharelatex-git-integration identifier
# The project title, if not null, is also always appended to the message.
#------------------------------------------------------------------------------
def commit_all_changes(message, title):
    run_cmd('git add -A .')
    run_cmd('git add -A {}'.format(get_git_ignore()))
    if title:
        cmd = 'git commit -m"[sharelatex-git-integration {} {}]'.format(title, get_timestamp())
    else:
        cmd = 'git commit -m"[sharelatex-git-integration {}]'.format(get_timestamp())
    if message:
        run_cmd('{} {}"'.format(cmd,message))
    else:
        run_cmd('{}"'.format(cmd))

#------------------------------------------------------------------------------
# Check if any files have changed. This exploits the git status command on the
# current directory
#------------------------------------------------------------------------------
def files_changed():
    out = run_cmd('git status .').decode('utf-8')
    return 'nothing to commit, working directory clean' not in out.lower()

#------------------------------------------------------------------------------
# Download the sharelatex project and extract it. Die out if there's any
# problem (e.g. bad ID, bad network connection or private project).
#
# Return the project title (null if it can't be determined).
#------------------------------------------------------------------------------
def fetch_updates(url, email, password):
    file_name = 'sharelatex.zip'

    base_url = extract_base_url(url)
    login_url = "{}/login".format(base_url)
    download_url = "{}/download/zip".format(url)
    
    Logger().log("Downloading files from {}...".format(download_url))

    try:
        s = requests.Session()
        
        if email is not None:
            if password is None:
                password = getpass.getpass("Enter password: ")
            Logger().log("Logging in {} with user {}...".format(login_url, email))
            r = s.get(login_url)
            csrf = BeautifulSoup(r.text).find('input', { 'name' : '_csrf' })['value']
            s.post(login_url, { '_csrf' : csrf , 'email' : email , 'password' : password })

        r = s.get(download_url, stream=True)
        with open(file_name, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024): 
                if chunk:
                    f.write(chunk)
    except:
        Logger().fatal_error('Could not retrieve files. Perhaps a temporary network failure? Invalid id?')
    
    Logger().log("Decompressing files...")
    
    try:
        with ZipFile(file_name, 'r') as f:
            f.extractall()
    except BadZipFile:
        os.remove(file_name)
        Logger().fatal_error("Downloaded file is not a zip file. Make sure that your project is public or you have provided a valid e-mail and password?")

    os.remove(file_name)

    try:
        u = urllib.request.urlopen(url)
        return re.compile("<title.*?>(.+?) - ShareLaTeX, Online LaTeX Editor</title>", re.I).findall(u.read().decode())[0]
    except:
        return None
#------------------------------------------------------------------------------
# Fetch the config value of the sharelatex document/project from a previous
# invocation
# These should be stored in a .sharelatex-git file.
#------------------------------------------------------------------------------
def read_saved_config_value(key):
    doc = '.sharelatex-git'

    try:
        config = configparser.ConfigParser()
        config.read(doc)
        return config['sharelatex'][key]
    except:
        return None

#------------------------------------------------------------------------------
# Write the key value of the sharelatex document/project so that future
# invocations do not require it. This is stored in a .sharelatex-git file.
#------------------------------------------------------------------------------
def write_saved_config_value(key, value):
    doc = '.sharelatex-git'

    try:
        config = configparser.ConfigParser()
        config.read(doc)
        if not config.has_section('sharelatex'):
            config['sharelatex'] = {}
        config['sharelatex'][key] = value
        with open(doc, 'w') as configfile:
            config.write(configfile)
    except:
       Logger().log("Problem creating .sharelatex-git file", True, 'YELLOW')

#------------------------------------------------------------------------------
# Given a key value passed by the user (potentially None/empty), as well as
# the .sharelatex-git file from previous invocations, determine the key value
# of the sharelatex project. In case of conflict, ask the user, but default to
# the one that he/she supplied.
#------------------------------------------------------------------------------
def determine_config_value(key, value):
    saved_value = read_saved_config_value(key)
    if value and saved_value:
        if value != saved_value:
            while True:
                print(
                    'Conflicting {key_name}. Given {old}, but previous records show {new}. Which to use?\n1. {old} [old]\n2. {new} [new]'.format(
                        key_name=key, old=saved_url, new=url))
                ans = input('Id to use [blank = 2.] -> ')
                if ans.strip() == '':
                    ans = '2'
                if ans.strip() == '1' or ans.strip() == '2':
                    break
            value = saved_value if int(ans.strip()) == 1 else value
    elif saved_value:
        value = saved_value

    return value

#------------------------------------------------------------------------------
# EXPERIMENTAL. Do a git push. FIXME
#------------------------------------------------------------------------------
def git_push():
    Logger().log(
        'Pushing is an experimental feature. If you experience lockdowns, hit CTRL+C. It means you probably have not configured password aching and/or passwordless pushes.',
        True, 'YELLOW')
    run_cmd('git push origin master')

#------------------------------------------------------------------------------
# The body of the application. Determine the ids, make sure we're in a git
# repository with all the right gitignore files, fetch the project files,
# commit any changes and also push them if the user requested.
#------------------------------------------------------------------------------
def go(url, email, password, message, push, dont_commit):
    url = determine_config_value('url', url)
    email = determine_config_value('email', email)

    if url is None:
        Logger().fatal_error('No url supplied! See (-h) for usage.')
    
    ensure_git_repository_started()
    ensure_gitignore_is_fine()
    project_title=fetch_updates(url, email, password)

    if not dont_commit:
        if files_changed():
            if message:
                Logger().log('Comitting changes. Message: {}.'.format(message))
            else:
                Logger().log('Comitting changes. No message.')
            commit_all_changes(message, project_title)

            if push:
                git_push()
        else:
            Logger().log('No changes to commit.')

    write_saved_config_value('url', url)
    write_saved_config_value('email', email)
    Logger().log('All done!')

#------------------------------------------------------------------------------
# Determine the URL from user-supplied input. The user can supply a URL or
# the ID directly. Note that the user can even pass the ZIP URL directly, as
# the regex catches only the relevant portion.
#------------------------------------------------------------------------------
def normalize_input(i):
    if 'http:' in i.lower() or 'https:' in i.lower():
        try:
            p = re.compile("(http.*/project/[a-zA-Z0-9]*).*", re.IGNORECASE)
            return p.search(i).group(1)
        except:
            Logger().fatal_error('Unrecognized url supplied ({})'.format(i))
    else:
        p = re.compile("[a-zA-Z0-9]*")
        if p.match(i):
            return 'https://www.sharelatex.com/project/{}'.format(i)
        else:
            Logger().log('Unrecognized id supplied ({})'.format(i))

#------------------------------------------------------------------------------
# Extract the base URL from the project's full URL
#------------------------------------------------------------------------------
def extract_base_url(url):
    try:
        p = re.compile("(http.*)/project/[a-zA-Z0-9]*", re.IGNORECASE)
        return p.search(url).group(1)
    except:
        Logger().fatal_error('Unexpected url format ({}), unable to extract service\'s base url'.format(url))

#------------------------------------------------------------------------------
# Parse user input.
#------------------------------------------------------------------------------
def parse_input():
    parser = OptionParser("usage: %prog [options] [url|id].\n"
    "e.g.\n\t%prog -m 'Wrote Thesis introduction' https://www.sharelatex.com/project/56147712cc7f5d0adeadbeef\n"
    "\t%prog -m 'Wrote Thesis introduction' 56147712cc7f5d0adeadbeef\n"
    "\t%prog -m 'Wrote Thesis introduction'                                                            [id from last invocation is used]\n"
    "\t%prog                                                                                           [id from last invocation is used, nothing is added to commit message]")
    parser.add_option('-m', '--message', help='Commit message (default: "").', dest='message', type='string', default='')
    parser.add_option('-p', "--push", help="Push after doing commit (default: don't push) [EXPERIMENTAL]", dest='do_push', action='store_true',default=False)
    parser.add_option('-n', "--no-commit", help="Don't commit, just download new files.",dest='dont_commit', action='store_true', default=False)
    parser.add_option('-e', '--email', help='E-mail needed for login', dest='email', action='store', type='string')
    parser.add_option('--password', help='Password to authenticate with the given e-mail', dest='password', type='string')

    (options, args) = parser.parse_args()

    if len(args) == 1:
        url = normalize_input(args[0])
    elif len(args) > 1:
        parser.error('Too many arguments.')
    else:
        url = None

    return url, options.email, options.password, options.message, options.do_push, options.dont_commit

#------------------------------------------------------------------------------
# Go, go, go!
#------------------------------------------------------------------------------
go(*parse_input())