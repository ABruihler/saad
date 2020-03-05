#!/usr/bin/env python3

import argparse
import http.server
import json
import os
import socketserver
import sys
import tempfile
import subprocess
import threading

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
    output, error = script.communicate()

    print(command, output.decode('utf-8'), error.decode('utf-8'))

    return output.decode('utf-8')


class Handler(http.server.BaseHTTPRequestHandler):
    timeout = 5

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

        if self.path == '/logs':
            self.wfile.write(get_logs().encode())
        else:
            self.wfile.write('saad server :\'(\n\n'.encode())
            self.wfile.write(('path: ' + self.path).encode())

    def do_POST(self):
        request_path = self.path

        # Git webhook for running SAAD on a repo
        if self.headers.get('content-type') != 'application/json':
            self.send_response(415)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write('request must have content-type application/json\n'.encode())
            return

        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)

        try:
            params = json.loads(body.decode('utf-8'))
        except ValueError:
            self.send_response(415)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write('data must be json\n'.encode())
            return

        try:
            ref = params['ref']
            previous_commit = params['before']
            current_commit = params['after']
            clone_url = params['repository']['clone_url']
        except KeyError:
            self.send_response(415)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write('data must be from Github webhook\n'.encode())
            return

        self.send_response(200)
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
