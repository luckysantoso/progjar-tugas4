from socket import *
import socket
import time
import sys
import logging
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from http import HttpServer

httpserver = HttpServer()

#untuk menggunakan threadpool executor, karena tidak mendukung subclassing pada process,
#maka class ProcessTheClient dirubah dulu menjadi function, tanpda memodifikasi behaviour didalamnya

def ProcessTheClient(connection, address):
    rcv = b""  # mulai dari bytes, bukan string
    connection.settimeout(60)  # timeout 60 detik untuk file besar
    
    while True:
        try:
            data = connection.recv(65536)  # buffer besar
            if data:
                rcv += data

                if b"\r\n\r\n" in rcv:
                    header_end = rcv.find(b"\r\n\r\n")
                    header = rcv[:header_end].decode(errors='ignore')

                    content_length = 0
                    for line in header.split("\r\n"):
                        if line.lower().startswith("content-length:"):
                            content_length = int(line.split(":")[1].strip())
                            break

                    body_start = header_end + 4
                    body_received = len(rcv) - body_start

                    if content_length > 0 and body_received < content_length:
                        while body_received < content_length:
                            more = connection.recv(65536)
                            if not more:
                                break
                            rcv += more
                            body_received = len(rcv) - body_start

                    hasil = httpserver.proses(rcv.decode('utf-8', errors='ignore'))
                    connection.sendall(hasil)
                    connection.close()
                    return

                elif b"GET" in rcv and rcv.endswith(b"\r\n\r\n"):
                    hasil = httpserver.proses(rcv.decode('utf-8', errors='ignore'))
                    connection.sendall(hasil)
                    connection.close()
                    return
            else:
                break
        except socket.timeout:
            print("Connection timeout")
            break
        except OSError as e:
            print(f"Socket error: {e}")
            break
    connection.close()
    return

def Server():
	the_clients = []
	my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

	my_socket.bind(('0.0.0.0', 8889))
	my_socket.listen(1)

	with ThreadPoolExecutor(20) as executor:
		while True:
				connection, client_address = my_socket.accept()
				#logging.warning("connection from {}".format(client_address))
				p = executor.submit(ProcessTheClient, connection, client_address)
				the_clients.append(p)
				#menampilkan jumlah process yang sedang aktif
				jumlah = ['x' for i in the_clients if i.running()==True]
				print(jumlah)

def main():
	Server()

if __name__=="__main__":
	main()