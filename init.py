#!/usr/bin/env python3

import argparse
import hashlib
import http.server
import json
import logging
import os
import re
import socketserver
import subprocess
import sys
import tempfile
import threading
from http import HTTPStatus

import core

DEFAULT_PORT = 8080

parser = argparse.ArgumentParser(description='Run saad')
parser.add_argument('--port',
                    help='HTTP server port (default is ' + str(DEFAULT_PORT) + ')',
                    type=int, default=DEFAULT_PORT)

parser.add_argument('--previous_commit', type=str)
parser.add_argument('--current_commit', type=str)
parser.add_argument('--clone_url', type=str)

args = parser.parse_args()

httpd = None

root_path = os.path.dirname(os.path.abspath(__file__))
os.chdir(root_path)


def update_self(server, script_args):
    print('RESTARTING')

    print('shutting down http server...')
    server.shutdown()
    server.server_close()

    print('making sure we are in current directory...')
    os.chdir(root_path)
    print('current directory:', os.getcwd())

    print('pulling new code from git...')
    os.system('git pull')

    print('installing dependencies')
    os.system('python3 -m pip install --user -r requirements.txt')

    print('starting new code...')
    os.execv(script_args[0], script_args)


def run_on_git(clone_url, current_commit, previous_commit):
    with tempfile.TemporaryDirectory() as previous_dirname:
        with tempfile.TemporaryDirectory() as current_dirname:
            print('################')
            print('Cloning previous commit...\n')
            os.chdir(previous_dirname)
            os.system('git clone ' + clone_url + ' .')
            os.system('git config --local advice.detachedHead false')
            os.system('git checkout ' + previous_commit)
            print()

            print('################')
            print('Cloning current commit...\n')
            os.chdir(current_dirname)
            os.system('git clone ' + clone_url + ' .')
            os.system('git config --local advice.detachedHead false')
            os.system('git checkout ' + current_commit)

            os.chdir(root_path)

            print('################')
            print('Running probes...\n')
            core.iterate_over_configs(current_dirname, previous_dirname)

            print('################')
            print('Complete!\n')


def get_logs():
    command = 'journalctl -n 500 --no-pager -u saad_python_service.service'
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
            valid = hashed == '33d76cd28b1a956224cd74a874a6ee84f473d28c64d7e4cd7356642c68d20fb3'
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
        # Content-type is set to application/problem+json and the status code is set as specified.
        # (See RFC 7807: <https://tools.ietf.org/html/rfc7807>)
        self.send_response(code)
        self.send_header('Content-type', 'application/problem+json')
        self.end_headers()
        self.wfile.write(message.encode())

    def do_GET(self):
        if self.path == '/logs':
            if self.handle_auth():
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(get_logs().encode())
            return
        elif self.path == '/modules':
            if self.handle_auth():
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(core.modules).encode())
            return
        elif re.match(r'/probes/(.+)', self.path):
            if self.handle_auth():
                repo_url = re.match(r'/probes/(.+)', self.path).group(1)
                if repo_url == 'https://github.com/skimberk/saad.git':  # TODO handle different repos
                    with tempfile.TemporaryDirectory() as dir:
                        os.chdir(dir)
                        os.system('git clone ' + repo_url + ' .')

                        path = os.path.join(dir, "probe_configs")  # TODO more versatile searching?
                        probes = list(core.all_json_in_dir(path))

                    self.send_response(HTTPStatus.OK)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(probes).encode())
                else:
                    return self.write_json_problem_details(HTTPStatus.UNPROCESSABLE_ENTITY,
                                                           "{\"title\": \"Invalid repo URL\","
                                                           "\"detail\": \"Provided repo <" + repo_url + "> is not tracked.\"}")
            return
        elif self.path == "/":
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()

            self.wfile.write('saad.sebastian.io\n'.encode())
            self.wfile.write('See https://github.com/skimberk/saad'.encode())
            return
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()

            self.wfile.write('Page not found :\'(\n\n'.encode())
            self.wfile.write(('path: ' + self.path).encode())
            return

    def do_POST(self):
        request_path = self.path

        # Git webhook for running SAAD on a repo
        if self.headers.get('content-type') != 'application/json':
            return self.write_json_problem_details(HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                                                   "{\"title\": \"Invalid content-type\","
                                                   "\"detail\": \"Expected request to have content-type application/json (got " + self.headers.get('content-type') + ")\"}")

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

        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('running...\n'.encode())

        if request_path == '/update':
            new_args = [sys.argv[0], '--clone_url', clone_url,
                        '--current_commit', current_commit,
                        '--previous_commit', previous_commit]

            threading.Thread(target=update_self, args=(httpd, new_args,)).start()
        elif request_path == '/run':
            run_on_git(clone_url, current_commit, previous_commit)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    timeout = 5
    allow_reuse_address = True


httpd = ThreadedTCPServer(('', args.port), Handler)

if args.previous_commit and args.current_commit and args.clone_url:
    print('Running on self', args.clone_url, args.current_commit, args.previous_commit)
    func_args = (args.clone_url, args.current_commit, args.previous_commit,)
    threading.Thread(target=run_on_git, args=func_args).start()

print('server at port', args.port)
httpd.serve_forever()
