"""TEST/DEVELOPMENT ONLY: explicit loopback static artifact; never imported by producer."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading


@contextmanager
def serve(html,*,port=0):
  if (type(html) is not bytes or not 0<len(html)<=32*1024*1024
      or b'NO INDEPENDENT LANE TRUTH' not in html or b'SYNTHETIC / NOT VEHICLE TRUTH' not in html):
    raise ValueError('SYNTHETIC_VIEWER_ARTIFACT_REQUIRED')
  if type(port) is not int or not 0<=port<=65535:
    raise ValueError('INVALID_LOOPBACK_PORT')

  class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):
      pass

    def do_GET(self):
      host=self.headers.get('Host','')
      if host not in ('127.0.0.1:'+str(self.server.server_port),'localhost:'+str(self.server.server_port)):
        self.send_error(403)
        return
      if self.client_address[0]!='127.0.0.1' or self.path!='/viewer.html':
        self.send_error(404)
        return
      self.send_response(200)
      self.send_header('Content-Type','text/html; charset=utf-8')
      self.send_header('Content-Length',str(len(html)))
      self.send_header('Cache-Control','no-store')
      self.send_header('X-Content-Type-Options','nosniff')
      self.end_headers()
      self.wfile.write(html)

    def do_POST(self):
      self.send_error(405)

    do_PUT=do_DELETE=do_PATCH=do_POST

  server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
  server.daemon_threads=True
  thread=threading.Thread(target=server.serve_forever,daemon=True)
  thread.start()
  try:
    yield server
  finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)


if __name__=='__main__':
  import argparse
  import time
  import signal
  parser=argparse.ArgumentParser(description='Temporary test-only loopback single-artifact viewer.')
  parser.add_argument('--html',type=Path,required=True)
  parser.add_argument('--port',type=int,default=0)
  parser.add_argument('--duration-s',type=int,default=120)
  args=parser.parse_args()
  if not 1<=args.duration_s<=300:
    parser.error('duration must be bounded 1..300 seconds')
  def stop(signum,frame):
    raise KeyboardInterrupt
  signal.signal(signal.SIGTERM,stop)
  with serve(args.html.read_bytes(),port=args.port) as server:
    print('http://127.0.0.1:'+str(server.server_address[1])+'/viewer.html',flush=True)
    try:
      time.sleep(args.duration_s)  # bounded test process
    except KeyboardInterrupt:
      pass  # context finally closes listener for SIGINT/SIGTERM too
