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
from http import HTTPStatus
from os.path import basename
from typing import Final

import core

DEFAULT_PORT: Final = 8080
ALLOWED_REPO_URLS = {"https://github.com/skimberk/saad.git", "https://github.com/skimberk/saad_example.git"}
SERVER_REPO_URL: Final = "https://github.com/skimberk/saad.git"  # Server only updates from one repo
WEB_ROOT: Final = os.getcwd() + "/website"

parser = argparse.ArgumentParser(description="Run saad")
parser.add_argument('--port',
                    help="HTTP server port (default is " + str(DEFAULT_PORT) + ")",
                    type=int, default=DEFAULT_PORT)

parser.add_argument('--previous_commit', type=str)
parser.add_argument('--current_commit', type=str)
parser.add_argument('--clone_url', type=str)

args = parser.parse_args()

if (args.clone_url is not None) and (args.clone_url not in ALLOWED_REPO_URLS):
    logging.info("Adding command line URL to ALLOWED_URLs: " + args.clone_url)
    ALLOWED_REPO_URLS.add(args.clone_url)

httpd = None

root_path = os.path.dirname(os.path.abspath(__file__))
os.chdir(root_path)


def update_self(server, script_args):
    print("RESTARTING")

    print("shutting down http server...")
    server.shutdown()
    server.server_close()

    print("making sure we are in current directory...")
    os.chdir(root_path)
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
    if url in ALLOWED_REPO_URLS:
        return True
    else:
        logging.info("Invalid repo URL: " + url)
        return False


def run_on_git(clone_url, current_commit, previous_commit):
    if not check_repo_url(clone_url):
        logging.warning("Not running due to invalid repo URL:" + clone_url)
        return False
    with tempfile.TemporaryDirectory() as previous_dirname:
        with tempfile.TemporaryDirectory() as current_dirname:
            print("################")
            print("Cloning previous commit...\n")
            os.chdir(previous_dirname)
            os.system("git clone " + clone_url + " .")
            os.system("git config --local advice.detachedHead false")
            os.system("git checkout " + previous_commit)
            print()

            print("################")
            print("Cloning current commit...\n")
            os.chdir(current_dirname)
            os.system("git clone " + clone_url + " .")
            os.system("git config --local advice.detachedHead false")
            os.system("git checkout " + current_commit)

            os.chdir(root_path)

            print("################")
            print("Running probes...\n")
            core.iterate_over_configs(current_dirname, previous_dirname)

            print("################")
            print("Complete!\n")


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
        if self.path == "/logs":
            if self.handle_auth():
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(get_logs().encode())
            return
        elif self.path == "/api/modules":
            if self.handle_auth():
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                data = {}
                for name, module in core.modules.items():
                    data[name] = module.config
                    
                self.wfile.write(json.dumps(data).encode())
            return
        elif self.path == "/modules":
            if self.handle_auth():
                data = {}
                forms=[]
                for name, module in core.modules.items():
                    data[name] = [module.config, module.get_inputs()]
                    form='<form action="/run/module" method="post"> <input type="submit" value="'+name+'"> <input type="hidden" id="'+name+'" name="module_name" value="'+name+'">'
                    for i in data[name][1]:
                        form+='<label for="'+i+'">'+i+'</label>  <input type="text" id="'+i+'" name="'+i+'" value="">'
                    form+='</form>'
                    forms.append(form)
                datajson = json.dumps(data, indent=4)
                outhtml=""
                for i in forms:
                    outhtml+=i
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()

                with open(WEB_ROOT + "/modules.html", 'rb') as file:
                    self.wfile.write(file.read()
                                     .replace("{{modules}}".encode(), outhtml.encode()))
            return
        elif self.path[:len("/api/probes/")] == "/api/probes/":
            if self.handle_auth():
                repo_url = self.path[len("/api/probes/"):]
                if check_repo_url(repo_url):
                    with tempfile.TemporaryDirectory() as dir:
                        os.chdir(dir)
                        os.system("git clone " + repo_url + " .")

                        path = os.path.join(dir, "probe_configs")  # TODO more versatile searching?
                        probes = list(core.all_json_in_dir(path))

                    self.send_response(HTTPStatus.OK)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(probes).encode())
                else:
                    return self.write_json_problem_details(HTTPStatus.UNPROCESSABLE_ENTITY,
                                                           "{\"title\": \"Invalid repo URL\","
                                                           "\"detail\": \"Provided repo <" + repo_url + "> is not tracked.\"}")
            return
        elif self.path[:len("/probes/")] == "/probes/":
            if self.handle_auth():
                repo_url = self.path[len("/probes/"):]
                repo_name = basename(repo_url)
                if repo_name[-len(".git"):] == ".git":
                    repo_name = repo_name[:len(".git")]

                if check_repo_url(repo_url):
                    with tempfile.TemporaryDirectory() as dir:
                        os.chdir(dir)
                        os.system("git clone " + repo_url + " .")
                        path = os.path.join(dir, "probe_configs")
                                # TODO more versatile searching?
                        probes = list(core.all_json_in_dir(path))
                    datajson = json.dumps(probes, indent=4)

                    self.send_response(HTTPStatus.OK)
                    self.send_header('Content-Type', 'text/html')
                    self.end_headers()

                    with open(WEB_ROOT + "/probes.html", 'rb') as file:
                        self.wfile.write(file.read()
                                         .replace("{{probes}}".encode(), datajson.encode())
                                         .replace("{{repo_url}}".encode(), repo_url.encode())
                                         .replace("{{repo_name}}".encode(), repo_name.encode()))
                        return
                else:
                    # TODO return user friendly details
                    return self.write_json_problem_details(HTTPStatus.UNPROCESSABLE_ENTITY,
                                                           "{\"title\": \"Invalid repo URL\","
                                                           "\"detail\": \"Provided repo <" + repo_url + "> is not tracked.\"}")
            return
        elif self.path == "/api/running":
            if self.handle_auth():
                data = core.get_all_probes()

                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'text/plain')  # TODO return proper formatted JSON
                self.end_headers()

                for probe in data:
                    self.wfile.write((str(probe) + "\n").encode())
            return
        elif self.path == "/":
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()

            with open(WEB_ROOT + "/root.html", 'rb') as file:
                self.wfile.write(file.read())
            return
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()

            self.wfile.write("Page not found :\'(\n\n".encode())
            self.wfile.write(("path: " + self.path).encode())
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
                if check_repo_url(clone_url):
                    self.send_response(HTTPStatus.OK)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write("Running...\n".encode())

                    return run_on_git(clone_url, current_commit, previous_commit)
                else:
                    return self.write_json_problem_details(HTTPStatus.UNPROCESSABLE_ENTITY,
                                                           "{\"title\": \"Invalid repo URL\","
                                                           "\"detail\": \"Provided repo <" + clone_url + "> is not tracked.\"}")
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
