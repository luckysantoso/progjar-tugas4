import sys
import os
import os.path
import uuid
from glob import glob
from datetime import datetime
import base64
import mimetypes

class HttpServer:
    def __init__(self):
        self.sessions={}
        self.types={}
        self.types['.pdf']='application/pdf'
        self.types['.jpg']='image/jpeg'
        self.types['.txt']='text/plain'
        self.types['.html']='text/html'
    def response(self, kode=404, message='Not Found', messagebody=bytes(), headers=None):
        if headers is None:
            headers = {}
        tanggal = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        resp = []
        resp.append(f"HTTP/1.1 {kode} {message}\r\n") 
        resp.append(f"Date: {tanggal}\r\n")
        resp.append("Connection: close\r\n")
        resp.append("Server: myserver/1.0\r\n")
        resp.append(f"Content-Length: {len(messagebody)}\r\n")
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'text/plain'
        for kk, vv in headers.items():
            resp.append(f"{kk}: {vv}\r\n")
        resp.append("\r\n")

        if not isinstance(messagebody, bytes):
            messagebody = messagebody.encode()
        return ''.join(resp).encode() + messagebody

    def proses(self, data):
        header_end = data.find(b"\r\n\r\n" if isinstance(data, bytes) else "\r\n\r\n")
        if header_end != -1:
            if isinstance(data, bytes):
                header = data[:header_end].decode('utf-8', errors='ignore')
                body = data[header_end + 4:]
            else:
                header = data[:header_end]
                body = data[header_end + 4:]
        else:
            header = data if isinstance(data, str) else data.decode('utf-8', errors='ignore')
            body = ""

        request_line = header.split("\r\n")[0]
        tokens = request_line.split(" ")
        if len(tokens) < 3 or not tokens[2].startswith("HTTP/"):
            return self.response(400, 'Bad Request', 'Malformed request line')

        method = tokens[0].upper()
        uri = tokens[1]
        version = tokens[2]

        header_lines = header.split("\r\n")[1:]
        headers = {}
        for line in header_lines:
            if ":" in line:
                key, val = line.split(":", 1)
                headers[key.strip().lower()] = val.strip()

        if version == 'HTTP/1.1' and 'host' not in headers:
            return self.response(400, 'Bad Request', 'Missing Host header')

        try:
            if method == 'GET':
                return self.http_get(uri)
            elif method == 'HEAD':
                return self.http_get(uri, head_only=True)
            elif method == 'POST':
                ctype = headers.get("content-type", "")
                if "application/x-www-form-urlencoded" not in ctype:
                    return self.response(415, 'Unsupported Media Type', 'Expected application/x-www-form-urlencoded')
                return self.http_post(uri, body)
            else:
                return self.response(501, 'Not Implemented', 'Method not implemented')
        except Exception as e:
            return self.response(500, 'Internal Server Error', str(e))

    def http_get(self, uri, head_only=False):
        if uri == '/list':
            entries = os.listdir('.')
            display = []
            for e in entries:
                if os.path.isdir(e):
                    display.append(f'./{e}/')
                else:
                    display.append(f'./{e}')
            body = '\n'.join(display)
            if head_only:
                return self.response(200, 'OK', '', {'Content-Type': 'text/plain'})
            return self.response(200, 'OK', body, {'Content-Type': 'text/plain'})

        if uri.startswith('/delete/'):
            fname = uri.split('/delete/')[1]
            if os.path.isfile(fname):
                try:
                    os.remove(fname)
                    return self.response(200, 'OK', f'Deleted {fname}')
                except Exception as e:
                    return self.response(500, 'Internal Server Error', str(e))
            return self.response(404, 'Not Found', '')

        path = uri.lstrip('/')
        if not os.path.isfile(path):
            return self.response(404, 'Not Found', '')
        with open(path, 'rb') as f:
            data = f.read()
        ctype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        if head_only:
            return self.response(200, 'OK', '', {'Content-Type': ctype})
        return self.response(200, 'OK', data, {'Content-Type': ctype})

    def http_post(self, uri, body):
        if uri == '/upload':
            try:
                parts = dict(item.split('=', 1) for item in body.split('&') if '=' in item)
                filename = parts.get('filename')
                b64data = parts.get('data')
                if not filename or not b64data:
                    raise ValueError("Missing filename or data")
                filedata = base64.b64decode(b64data)
                with open(filename, 'wb') as f:
                    f.write(filedata)
                return self.response(201, 'Created', f'Uploaded {filename}', {'Content-Type': 'text/plain'})
            except Exception as e:
                return self.response(400, 'Bad Request', str(e), {'Content-Type': 'text/plain'})
        return self.response(404, 'Not Found', '')


if __name__ == "__main__":
    httpserver = HttpServer()
    print(httpserver.proses('GET /list HTTP/1.1\r\nHost: localhost\r\n\r\n'))
    b64 = base64.b64encode(b'Hello').decode()
    print(httpserver.proses(f'POST /upload HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/x-www-form-urlencoded\r\n\r\nfilename=test.txt&data={b64}'))
    print(httpserver.proses('GET /test.txt HTTP/1.1\r\nHost: localhost\r\n\r\n'))
    print(httpserver.proses('GET /delete/test.txt HTTP/1.1\r\nHost: localhost\r\n\r\n'))
