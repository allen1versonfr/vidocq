"""Bounded loopback request workers; long operations cannot spawn unlimited threads."""
from http.server import ThreadingHTTPServer
import threading

class LocalHTTPServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,*args,**kwargs):
        self.capacity=threading.BoundedSemaphore(16)
        super().__init__(*args,**kwargs)
    def process_request(self,request,client_address):
        request.settimeout(30)
        if not self.capacity.acquire(blocking=False):
            try:request.sendall(b'HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
            finally:self.shutdown_request(request)
            return
        try:super().process_request(request,client_address)
        except Exception:self.capacity.release();raise
    def process_request_thread(self,request,client_address):
        try:super().process_request_thread(request,client_address)
        finally:self.capacity.release()
