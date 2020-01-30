#!/usr/bin/env python3

import http.server
import socketserver
import argparse
import os
import sys
import threading

DEFAULT_PORT = 8080

parser = argparse.ArgumentParser(description='Run saad')
parser.add_argument('--port',
        help='HTTP server port (default is ' + str(DEFAULT_PORT) + ')',
        type=int, default=DEFAULT_PORT)

args = parser.parse_args()

httpd = None

def update_self(server, script_location, script_args):
    print('RESTARTING')

    print('shutting down http server...')
    server.shutdown()
    server.server_close()

    print('current directory:', os.getcwd())

    print('pulling new code from git...')
    os.system('git pull')

    print('starting new code...')
    os.execv(script_location, script_args)

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('hello world 2.0\n\n'.encode())

        self.wfile.write(('path: ' + self.path).encode())

    def do_POST(self):
        request_path = self.path

        if request_path == '/update':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write('success\n'.encode())

            threading.Thread(target=update_self, args=(httpd, __file__, sys.argv,)).start()

socketserver.TCPServer.allow_reuse_address=True
httpd = socketserver.TCPServer(('', args.port), Handler)

print('server at port', args.port)
httpd.serve_forever()
