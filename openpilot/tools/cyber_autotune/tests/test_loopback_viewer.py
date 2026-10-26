"""Explicit test/development loopback exception; no production networking."""
import http.client
import socket
import unittest

from openpilot.tools.cyber_autotune.tests.loopback_viewer_server import serve

HTML=b'<!doctype html><p>NO INDEPENDENT LANE TRUTH - SYNTHETIC / NOT VEHICLE TRUTH</p>'


class TestLoopbackViewer(unittest.TestCase):
  def test_only_loopback_and_exact_artifact_route(self):
    with serve(HTML) as server:
      host,port=server.server_address
      self.assertEqual(host,'127.0.0.1')
      connection=http.client.HTTPConnection(host,port,timeout=3)
      connection.request('GET','/viewer.html')
      response=connection.getresponse()
      self.assertEqual(response.status,200)
      self.assertEqual(response.read(),HTML)
      connection.request('GET','/../raw.json')
      response=connection.getresponse()
      self.assertEqual(response.status,404)
      response.read()
      connection.close()

  def test_shutdown_releases_listener_even_on_exception(self):
    port=None
    with self.assertRaises(RuntimeError):
      with serve(HTML) as server:
        port=server.server_address[1]
        raise RuntimeError('simulated browser failure')
    with socket.socket() as client:
      client.settimeout(1)
      self.assertNotEqual(client.connect_ex(('127.0.0.1',port)),0)

  def test_private_artifact_scope_invalid_html_or_oversize_rejected(self):
    for content in (b'<p>private</p>',b'',b'x'*(32*1024*1024+1)):
      with self.assertRaises(ValueError):
        with serve(content):
          self.fail('must not start listener')

  def test_host_header_and_mutating_methods_rejected(self):
    with serve(HTML) as server:
      connection=http.client.HTTPConnection(*server.server_address,timeout=3)
      connection.request('GET','/viewer.html',headers={'Host':'external.example'})
      response=connection.getresponse()
      self.assertEqual(response.status,403)
      response.read()
      connection.request('POST','/viewer.html',body='mutation')
      response=connection.getresponse()
      self.assertEqual(response.status,405)
      response.read()
      connection.close()

if __name__=='__main__':
  unittest.main()
