import sys
import socket
import json
import logging
import ssl
import os
import base64


server_address = ('172.16.16.101', 8889)


def make_socket(destination_address='localhost', port=8889):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(120)
        sock.connect((destination_address, port))
        return sock
    except Exception as ee:
        logging.warning(f"error {str(ee)}")


def make_secure_socket(destination_address='localhost', port=8889):
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((destination_address, port))
        secure_socket = context.wrap_socket(sock, server_hostname=destination_address)
        return secure_socket
    except Exception as ee:
        logging.warning(f"error {str(ee)}")


def send_command(command_str, is_secure=False):
    alamat_server, port_server = server_address

    sock = make_secure_socket(alamat_server, port_server) if is_secure else make_socket(alamat_server, port_server)

    logging.warning(f"sending message:\n{command_str}")
    try:
        sock.sendall(command_str.encode())

        response = b""
        while b"\r\n\r\n" not in response:
            chunk = sock.recv(2048)
            if not chunk:
                break
            response += chunk

        header_part, body_part = response.split(b"\r\n\r\n", 1)
        headers = header_part.decode(errors='ignore').split("\r\n")

        content_length = 0
        for line in headers:
            if line.lower().startswith("content-length:"):
                content_length = int(line.split(":")[1].strip())
                break

        while len(body_part) < content_length:
            more = sock.recv(2048)
            if not more:
                break
            body_part += more

        return (header_part + b"\r\n\r\n" + body_part).decode(errors='ignore')

    except Exception as ee:
        logging.warning(f"error during data receiving {str(ee)}")
        return ''
    finally:
        sock.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)

    print('\n--- LIST DIRECTORY ---')
    cmd = 'GET /list HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n'
    print(send_command(cmd))

    print('\n--- UPLOAD FILE ---')
    filepath = 'client_image.jpg'
    if os.path.isfile(filepath):
        with open(filepath, 'rb') as f:
            filedata = f.read()
        filename = os.path.basename(filepath)
        filedata_b64 = base64.b64encode(filedata).decode()
        body = f'filename={filename}&data={filedata_b64}'
        content_length = len(body.encode())

        upload_request = (
            f'POST /upload HTTP/1.1\r\n'
            f'Host: localhost\r\n'
            f'Content-Length: {content_length}\r\n'
            f'Content-Type: application/x-www-form-urlencoded\r\n'
            f'Connection: close\r\n'
            f'\r\n'
            f'{body}'
        )

        print(send_command(upload_request))
    else:
        print(f'File {filepath} tidak ditemukan')

    print('\n--- LIST SETELAH UPLOAD ---')
    print(send_command('GET /list HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n'))

    print('\n--- LIHAT FILE ---')
    print(send_command('GET /deleteDummy.jpg HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n'))

    print('\n--- DELETE deleteDummy.jpg ---')
    delete_response = send_command('GET /delete/deleteDummy.jpg HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
    print(delete_response)

    print('\n--- LIST SETELAH DELETE ---')
    print(send_command('GET /list HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n'))

