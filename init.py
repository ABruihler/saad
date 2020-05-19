#!/usr/bin/env python3

import argparse
import hashlib
import http.server
import json
import logging
import os
import socketserver
import subprocess
import sys
import tempfile
import threading
import sqlite3
import urllib
import configparser
from http import HTTPStatus
from os.path import basename
from typing import Final

import core

DEFAULT_PORT: Final = 8080
ALLOWED_REPO_URLS = {"https://github.com/skimberk/saad.git", "https://github.com/skimberk/saad_example.git", "https://github.com/skimberk/saad_fuzzer_example.git"}
SERVER_REPO_URL: Final = "https://github.com/skimberk/saad.git"  # Server only updates from one repo

parser = argparse.ArgumentParser(description="Run saad")
parser.add_argument('--port',
                    help="HTTP server port (default is " + str(DEFAULT_PORT) + ")",
                    type=int, default=DEFAULT_PORT)

parser.add_argument('--previous_commit', type=str)
parser.add_argument('--current_commit', type=str)
parser.add_argument('--clone_url', type=str)
parser.add_argument('--master_config', type=str)
args = parser.parse_args()

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)  # Print all logs

serverRepo = core.Repo(SERVER_REPO_URL, 'Server', os.path.dirname(os.path.abspath(__file__)))
# Make sure we're in saad/ directory (important when running as a service)
os.chdir(serverRepo.config['root_path'])

if (args.master_config is not None) and os.path.isfile(args.master_config):
    serverRepo.load_config_recursive(args.master_config)
elif os.path.isfile("SAAD_config.cfg"):
    logging.info("Invalid master config file, running on default")
    serverRepo.load_config_recursive("SAAD_config.cfg")

else:
    logging.info("Can't find a master config, shutting down")
    # TODO: Shut down

if (args.clone_url is not None) and (args.clone_url not in ALLOWED_REPO_URLS):
    logging.info("Adding command line URL to ALLOWED_URLs: " + args.clone_url)
    ALLOWED_REPO_URLS.add(args.clone_url)

httpd = None
serverRepo.reload_all_modules()
print(serverRepo.config)
if 'ALLOWED_REPO_URLS' in serverRepo.config:
    for repo in serverRepo.config['ALLOWED_REPO_URLS']:
        core.Repo(serverRepo.config['ALLOWED_REPO_URLS'][repo], repo, serverRepo.config['root_path'], serverRepo)
for repo in serverRepo.child_repos.values():
    repo.load_config_recursive("", 'current', True)
for repo in serverRepo.child_repos.values():
    repo.reload_all_modules()


def update_self(server, script_args):
    print("RESTARTING")

    print("shutting down http server...")
    server.shutdown()
    server.server_close()

    print("making sure we are in current directory...")
    os.chdir(serverRepo.config['root_path'])
    print("current directory:", os.getcwd())

    print("pulling new code from git...")
    os.system("git pull")

    print("installing dependencies")
    os.system("python3 -m pip install --user -r requirements.txt")

    print("starting new code...")
    os.execv(script_args[0], script_args)


def check_repo_url(url) -> bool:
    # Check that a provided URL for a repo is allowed
    # TODO better storing/updating of the list
    if url in serverRepo.config['ALLOWED_REPO_URLS'].values():
        for key, val in serverRepo.config['ALLOWED_REPO_URLS'].items():
            if url == val:
                return key
        return False
    else:
        logging.info("Invalid repo URL: " + url)
        return False


def run_on_git(clone_url, current_commit, previous_commit):
    repo_name = check_repo_url(clone_url)
    if not repo_name:
        logging.warning("Not running due to invalid repo URL:" + clone_url)
        return False
    serverRepo.child_repos[repo_name].run_all_probes(current_commit, previous_commit)


def get_logs():
    command = "journalctl -n 500 --no-pager -u saad_python_service.service"
    script = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = script.communicate()  # TODO include a timeout value?

    output_text = output.decode('utf-8')
    error_text = error.decode('utf-8')

    return output_text


class Handler(http.server.BaseHTTPRequestHandler):
    timeout = 5

    def check_auth_header(self) -> bool:
        # Check the authorization header and return whether it is valid
        #print(self.headers)
        auth_header = self.headers.get('Authorization')
        if auth_header:
            hashed = hashlib.sha256(auth_header.encode('utf-8')).hexdigest()
            valid = hashed == "33d76cd28b1a956224cd74a874a6ee84f473d28c64d7e4cd7356642c68d20fb3"
            if valid:
                return True
            else:
                logging.info("Bad password attempt")
                return False
        else:
            return False

    def handle_auth(self) -> bool:
        # Checks authentication and handles writing a response if it is incorrect.
        if self.check_auth_header():
            return True
        else:
            self.send_response(HTTPStatus.UNAUTHORIZED)
            self.send_header('WWW-Authenticate', 'Basic')
            self.end_headers()
            # TODO try to block further writes?
            return False

    def write_json_problem_details(self, code, message):
        # Respond with a JSON problem details message
        # Content-Type is set to application/problem+json and the status code is set as specified.
        # (See RFC 7807: <https://tools.ietf.org/html/rfc7807>)
        self.send_response(code)
        self.send_header('Content-Type', 'application/problem+json')
        self.end_headers()
        self.wfile.write(message.encode())

    def do_GET(self):
        url_path=urllib.parse.urlparse(self.path).path
        get_args=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        #print(urllib.parse.urlparse(self.path))
        os.chdir(serverRepo.config['root_path'])
        logging.debug('Current working directory: {}'.format(os.getcwd()))

        if url_path == "/logs":
            if self.handle_auth():
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(get_logs().encode())
            return
        elif url_path == "/api/modules":
            if self.handle_auth():
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                data = {}
                repo = serverRepo
                if ('repo' in get_args) and get_args['repo'][0] in serverRepo.child_repos:
                    repo = serverRepo.child_repos[get_args['repo'][0]]
                for name, module in repo.modules.items():
                    data[name] = module.config

                self.wfile.write(json.dumps(data).encode())
            return
        elif url_path == "/modules":
            if self.handle_auth():
                print(vars(self))
                data = {}
                forms = []
                repo = serverRepo
                if ('repo' in get_args) and get_args['repo'][0] in serverRepo.child_repos:
                    repo = serverRepo.child_repos[get_args['repo'][0]]
                for name, module in repo.modules.items():
                    data[name] = [module.config, module.get_inputs()]
                    form = '<form action="/run/module" method="post"> <input type="submit" value="' + name + '"> <input type="hidden" id="' + name + '" name="module_name" value="' + name + '">'
                    form += '<input type="hidden" id="' + name + '_repo" name="repo_name" value="' + repo.name + '">'
                    for i in data[name][1]:
                        form += '<label for="' + i + '">' + i + '</label>  <input type="text" id="' + i + '" name="' + i + '" value="">'
                    form += '</form>'
                    forms.append(form)
                datajson = json.dumps(data, indent=4)
                outhtml = ""
                for i in forms:
                    outhtml += i

                try:
                    with open(serverRepo.config['web_root'] + "/modules.html", 'rb') as file:
                        self.send_response(HTTPStatus.OK)
                        self.send_header('Content-Type', 'text/html')
                        self.end_headers()

                        self.wfile.write(file.read()
                                         .replace("{{modules}}".encode(), outhtml.encode()))
                except FileNotFoundError as e:
                    logging.error("Missing website file", e)
                    self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                    self.end_headers()
            return
        elif url_path[:len("/api/probes")] == "/api/probes":
            if self.handle_auth():
                repo=False
                print(get_args)
                if ('repo' in get_args) and get_args['repo'][0] in serverRepo.child_repos:
                    repo=serverRepo.child_repos[get_args['repo'][0]]
                if repo:
                    probes = repo.load_probe_json()
                    os.chdir(serverRepo.config['root_path'])
                    self.send_response(HTTPStatus.OK)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(probes).encode())
                else:
                    repo=''
                    if ('repo' in get_args):
                        repo=get_args['repo'][0]
                    return self.write_json_problem_details(HTTPStatus.UNPROCESSABLE_ENTITY,
                                                           "{\"title\": \"Invalid repo URL\","
                                                           "\"detail\": \"Provided repo <" + repo + "> is not tracked.\"}")
            return
        elif url_path[:len("/probes")] == "/probes":
            if self.handle_auth():
                repo=False
                print(get_args)
                if ('repo' in get_args) and get_args['repo'][0] in serverRepo.child_repos:
                    repo=serverRepo.child_repos[get_args['repo'][0]]
                if repo:
                    probes = repo.load_probe_json()
                    os.chdir(serverRepo.config['root_path'])
                    datajson = json.dumps(probes, indent=4)

                    try:
                        with open(serverRepo.config['web_root'] + "/probes.html", 'rb') as file:
                            self.send_response(HTTPStatus.OK)
                            self.send_header('Content-Type', 'text/html')
                            self.end_headers()

                            self.wfile.write(file.read()
                                             .replace("{{probes}}".encode(), datajson.encode())
                                             .replace("{{repo_url}}".encode(), repo.repo.encode())
                                             .replace("{{repo_name}}".encode(), repo.name.encode()))
                    except FileNotFoundError as e:
                        logging.error("Missing website file", e)
                        self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                        self.end_headers()
                else:
                    repo=''
                    if ('repo' in get_args):
                        repo=get_args['repo'][0]
                    return self.write_json_problem_details(HTTPStatus.UNPROCESSABLE_ENTITY,
                                                           "{\"title\": \"Invalid repo URL\","
                                                           "\"detail\": \"Provided repo <" + repo + "> is not tracked.\"}")
            return
        elif url_path == "/api/running":
            if self.handle_auth():
                repo = serverRepo
                if ('repo' in get_args) and get_args['repo'][0] in serverRepo.child_repos:
                    repo = serverRepo.child_repos[get_args['repo'][0]]
                data = repo.get_all_probes()

                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'text/plain')  # TODO return proper formatted JSON
                self.end_headers()

                for probe in data:
                    self.wfile.write((str(probe) + "\n").encode())
            return
        elif url_path == "/running":
            if self.handle_auth():
                repo = serverRepo
                if ('repo' in get_args) and get_args['repo'][0] in serverRepo.child_repos:
                    repo = serverRepo.child_repos[get_args['repo'][0]]
                data = repo.get_all_probes()

                datastring = "<ul>\n"
                for probe in data:
                    datastring += "<li><code>" + str(probe) + "</code></li>\n"
                datastring += "</ul>"

                try:
                    with open(serverRepo.config['web_root'] + "/running.html", 'rb') as file:
                        self.send_response(HTTPStatus.OK)
                        self.send_header('Content-Type', 'text/html')
                        self.end_headers()

                        self.wfile.write(file.read()
                                         .replace("{{running}}".encode(), datastring.encode()))
                except FileNotFoundError as e:
                    logging.error("Missing website file", e)
                    self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                    self.end_headers()

            return
        elif url_path == "/probelogs":
            if self.handle_auth():
                db_path = core.probe_db_path
                db = core.connect_database(db_path)
                cursor = db.cursor()
                probe_list_html = ""
                for probe_id in cursor.execute("SELECT id FROM probes"):
                    probe_list_html += '<li><ul style="display:inline;">'
                    cursor2 = db.cursor()
                    temp = cursor2.execute("SELECT * FROM probes WHERE id=?", (probe_id[0],))
                    for item in cursor2.execute("SELECT * FROM probes WHERE id=?", (probe_id[0],)):
                        for thing in item:
                            if not isinstance(thing, str):
                                probe_list_html += "<li style='display:inline;'> " + str(thing) + "</li>"
                            else:
                                probe_list_html += "<li style='display:inline;'> " + thing + "</li>"
                    for item in cursor2.execute("SELECT * FROM probe_inputs WHERE probe_id=?", (probe_id[0],)):
                        for thing in item[1:]:
                            if not isinstance(thing, str):
                                probe_list_html += "<li style='display:inline;'> " + str(thing) + "</li>"
                            else:
                                probe_list_html += "<li style='display:inline;'> " + thing + "</li>"
                    for item in cursor2.execute("SELECT * FROM probe_outputs WHERE probe_id=?", (probe_id[0],)):
                        for thing in item[1:]:
                            if not isinstance(thing, str):
                                probe_list_html += "<li style='display:inline;'> " + str(thing) + "</li>"
                            else:
                                probe_list_html += "<li style='display:inline;'> " + thing + "</li>"
                    probe_list_html += "</ul></li>"
                db.close()
                with open(serverRepo.config['web_root'] + "/probelogs.html", 'rb') as file:
                    self.send_response(HTTPStatus.OK)
                    self.send_header('Content-Type', 'text/html')
                    self.end_headers()

                    self.wfile.write(file.read()
                                     .replace("{{probes}}".encode(), probe_list_html.encode()))

        elif url_path == "/":
            try:
                with open(serverRepo.config['web_root'] + "/root.html", 'rb') as file:
                    self.send_response(HTTPStatus.OK)
                    self.send_header('Content-Type', 'text/html')
                    self.end_headers()

                    self.wfile.write(file.read())
            except FileNotFoundError as e:
                logging.error("Missing website file", e)
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.end_headers()
            return
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()

            self.wfile.write("Page not found :\'(\n\n".encode())
            self.wfile.write(("path: " + url_path).encode())
            return

    def do_POST(self):
        if self.path == "/update" or self.path == "/run":
            # Git webhook for running SAAD on a repo
            if self.headers.get('Content-Type') != 'application/json':
                return self.write_json_problem_details(HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                                                       "{\"title\": \"Invalid Content-Type\","
                                                       "\"detail\": \"Expected request to have Content-Type application/json (got " + self.headers.get('Content-Type') + ")\"}")

            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)

            try:
                params = json.loads(body.decode('utf-8'))
            except ValueError:
                return self.write_json_problem_details(HTTPStatus.BAD_REQUEST,
                                                       "{\"title\": \"Invalid JSON data\","
                                                       "\"detail\": \"Unable to load given JSON data\"}")

            try:
                ref = params['ref']
                previous_commit = params['before']
                current_commit = params['after']
                clone_url = params['repository']['clone_url']
            except KeyError:
                return self.write_json_problem_details(HTTPStatus.BAD_REQUEST,
                                                       "{\"title\": \"Invalid JSON data\","
                                                       "\"detail\": \"Given JSON data missing expected field(s)\"}")

            if self.path == "/update":
                if clone_url == SERVER_REPO_URL:
                    self.send_response(HTTPStatus.OK)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write("Updating...\n".encode())
                    # TODO make sure response is sent?

                    new_args = [sys.argv[0], '--clone_url', clone_url,
                                '--current_commit', current_commit,
                                '--previous_commit', previous_commit]
                    return threading.Thread(target=update_self, args=(httpd, new_args,)).start()
                else:
                    return self.write_json_problem_details(HTTPStatus.UNPROCESSABLE_ENTITY,
                                                           "{\"title\": \"Invalid repo URL\","
                                                           "\"detail\": \"Will not update as the provided repo <" + clone_url + "> is not the expected server repo\"}")
            elif self.path == "/run":
                repo_name = check_repo_url(clone_url)
                if repo_name:
                    self.send_response(HTTPStatus.OK)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write("Running...\n".encode())
                    serverRepo.child_repos[repo_name].commits.pop('current',None)
                    return serverRepo.child_repos[repo_name].run_all_probes(current_commit, previous_commit)
                else:
                    return self.write_json_problem_details(HTTPStatus.UNPROCESSABLE_ENTITY,
                                                           "{\"title\": \"Invalid repo URL\","
                                                           "\"detail\": \"Provided repo <" + clone_url + "> is not tracked.\"}")
        elif self.path == "/run/module":  # TODO API?
            if self.handle_auth():
                content_length = int(self.headers['Content-Length'])
                body = self.rfile.read(content_length)

                data = {}
                for value in body.decode().split("&"):
                    data.update({value.split("=", 1)[0]: value.split("=", 1)[1]})

                module_name = data.pop("module_name")
                repo_name = data.pop("repo_name")
                repo = serverRepo
                if repo_name in serverRepo.child_repos:
                    repo = serverRepo.child_repos[repo_name]
                repo.modules[module_name].run_probe(data, core.Scope({}), repo)
            return
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()
            return


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    timeout = 5
    allow_reuse_address = True


httpd = ThreadedTCPServer(("", args.port), Handler)

if args.previous_commit and args.current_commit and args.clone_url:
    print("Running on self", args.clone_url, args.current_commit, args.previous_commit)
    func_args = (args.clone_url, args.current_commit, args.previous_commit,)
    threading.Thread(target=run_on_git, args=func_args).start()

print("server at port", args.port)
httpd.serve_forever()
