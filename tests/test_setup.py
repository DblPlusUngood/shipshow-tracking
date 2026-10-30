import importlib.util,sys,unittest,urllib.parse
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
import setup_local as m
KEY='00000000-0000-4000-8000-000000000001'
class Tests(unittest.TestCase):
 def invoke(self,origin='http://127.0.0.1:1234',token=m.TOKEN,host='127.0.0.1:1234',key=KEY,api_error=False):
  h=object.__new__(m.Handler);h.server=SimpleNamespace(allowed_host='127.0.0.1:1234');h.path='/'+m.TOKEN
  raw=urllib.parse.urlencode({'token':token,'key':key}).encode();h.rfile=BytesIO(raw)
  h.headers={'Host':host,'Content-Length':str(len(raw))}
  if origin is not None:h.headers['Origin']=origin
  result=[];h.respond=lambda status,body:result.append((status,body))
  with patch.object(m.shipshow,'fetch_trackings',return_value={'trackings':[],'has_more':False}) as fetch,patch.object(m.shipshow,'save_key') as save,patch('builtins.print'):
   if api_error:fetch.side_effect=m.shipshow.SafeError('Test rejection')
   h.do_POST()
   return result[0][0],fetch.call_count,save.call_count
 def test_same_origin(self):self.assertEqual(self.invoke(),(200,1,1))
 def test_opaque_origin(self):self.assertEqual(self.invoke(origin='null'),(200,1,1))
 def test_missing_origin(self):self.assertEqual(self.invoke(origin=None),(200,1,1))
 def test_external_origin_rejected(self):self.assertEqual(self.invoke(origin='https://example.com'),(403,0,0))
 def test_opaque_origin_requires_token(self):self.assertEqual(self.invoke(origin='null',token=''),(403,0,0))
 def test_missing_origin_requires_token(self):self.assertEqual(self.invoke(origin=None,token='wrong'),(403,0,0))
 def test_wrong_host_rejected(self):self.assertEqual(self.invoke(host='evil.test'),(403,0,0))
 def test_invalid_key(self):self.assertEqual(self.invoke(key='wrong'),(400,0,0))
 def test_rejected_api_key_not_saved(self):self.assertEqual(self.invoke(api_error=True),(400,1,0))
class LifecycleTests(unittest.TestCase):
 def test_setup_remains_open_after_thirty_minutes(self):
  def finish_after_second_request():
   if server.handle_request.call_count == 2: m.DONE=True
  with patch.object(m,'HTTPServer') as factory,patch.object(m.time,'monotonic',side_effect=[0,0,1860]),patch('builtins.print'):
   server=factory.return_value;server.server_port=1234
   server.handle_request.side_effect=finish_after_second_request
   m.run(port=1234)
   self.assertEqual(server.handle_request.call_count,2)
   server.server_close.assert_called_once()
 def test_setup_expires_after_eight_hours(self):
  with patch.object(m,'HTTPServer') as factory,patch.object(m.time,'monotonic',side_effect=[0,28801]),patch('builtins.print') as output:
   server=factory.return_value;server.server_port=1234
   m.run(port=1234)
   server.handle_request.assert_not_called()
   server.server_close.assert_called_once()
   output.assert_any_call('Setup window expired without saving a key.',flush=True)
 def test_setup_releases_port_after_interruption(self):
  with patch.object(m,'HTTPServer') as factory,patch.object(m.time,'monotonic',return_value=0),patch('builtins.print'):
   server=factory.return_value;server.server_port=1234
   server.handle_request.side_effect=KeyboardInterrupt
   with self.assertRaises(KeyboardInterrupt):m.run(port=1234)
   server.server_close.assert_called_once()
if __name__=='__main__':unittest.main(verbosity=2)
