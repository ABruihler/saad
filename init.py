#!/usr/bin/env python3

import http.server
import socketserver
import argparse
import os
import sys
import threading
import json
import tempfile
import module_runner

DEFAULT_PORT = 8080

parser = argparse.ArgumentParser(description='Run saad')
parser.add_argument('--port',
        help='HTTP server port (default is ' + str(DEFAULT_PORT) + ')',
        type=int, default=DEFAULT_PORT)

args = parser.parse_args()

httpd = None

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def update_self(server, script_location, script_args):
    print('RESTARTING')

    print('shutting down http server...')
    server.shutdown()
    server.server_close()

    print('current directory:', os.getcwd())
    print('making sure we are in current directory...')
    os.chdir(os.path.dirname(os.path.abspath(script_location)))
    print('current directory:', os.getcwd())

    print('pulling new code from git...')
    os.system('git pull')

    print('installing dependencies')
    os.system('python3 -m pip install --user -r requirements.txt')

    print('starting new code...')
    os.execv(script_location, script_args)

def run_on_git(clone_url, current_commit, previous_commit):
    with tempfile.TemporaryDirectory() as previous_dirname:
        with tempfile.TemporaryDirectory() as current_dirname:
            startdir=os.path.dirname(os.path.abspath(__file__))
            os.chdir(previous_dirname)
            os.system('git clone ' + clone_url + ' .')
            os.system('git checkout ' + previous_commit)

            os.chdir(current_dirname)
            os.system('git clone ' + clone_url + ' .')
            os.system('git checkout ' + current_commit)

            os.chdir(startdir)
            # Run probes!
            module_runner.iterate_over_configs(current_dirname, previous_dirname)

class Handler(http.server.BaseHTTPRequestHandler):
    timeout = 5

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('saad server :\'(\n\n'.encode())

        self.wfile.write(('path: ' + self.path).encode())

    def do_POST(self):
        request_path = self.path

        if request_path == '/update':
            # Updates SAAD's code by pulling from git and restarting
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write('updating...\n'.encode())

            threading.Thread(target=update_self, args=(httpd, __file__, sys.argv,)).start()
        elif request_path == '/run':
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

            run_on_git(clone_url, current_commit, previous_commit)
            print(clone_url, ref, current_commit, previous_commit)

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    timeout = 5
    allow_reuse_address = True

httpd = ThreadedTCPServer(('', args.port), Handler)

print('server at port', args.port)
httpd.serve_forever()
