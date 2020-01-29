import http.server
import socketserver
import argparse

DEFAULT_PORT = 8080

parser = argparse.ArgumentParser(description='Run saad')
parser.add_argument('--port',
        help='HTTP server port (default is ' + str(DEFAULT_PORT) + ')',
        type=int, default=DEFAULT_PORT)

args = parser.parse_args()

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('hello world\n\n'.encode())

        self.wfile.write(('path: ' + self.path).encode())

with socketserver.TCPServer(('', args.port), Handler) as httpd:
    print('server at port', args.port)
    httpd.serve_forever()
