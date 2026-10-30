import importlib.util, json, subprocess, sys, unittest, urllib.error
from unittest.mock import patch
from io import BytesIO
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts/shipshow.py'
spec=importlib.util.spec_from_file_location('shipshow',p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
KEY='00000000-0000-4000-8000-000000000001'
DATA={'trackings':[{'tracking_id':'t1','title':'Adapter','config':{'login':'private'},'extra':{'items':[{'price':2}]},'history':[{'message':'Signature required','timestamp':'2026-09-20T12:00:00','locationlat':44}], 'last_status':'transit'}],'categories':[],'hasmoredata':True}
class Response(BytesIO):
 def __enter__(self): return self
 def __exit__(self,*args): self.close()
class Tests(unittest.TestCase):
 def setUp(self): m.CACHE.clear(); m.LAST_REQUEST=None
 def test_no_write_tools(self):
  tools=m.handle({'jsonrpc':'2.0','id':1,'method':'tools/list'})['result']['tools']
  self.assertEqual({x['name'] for x in tools},{'list_shipments','connection_status'})
  self.assertTrue(all(x['annotations']['readOnlyHint'] for x in tools))
 def test_projection_and_unknown_money(self):
  result=m.normalize(DATA,'now'); row=result['trackings'][0]
  self.assertNotIn('config',row); self.assertEqual(row['extra_field_names'],['items'])
  self.assertNotIn('unit_price',row); self.assertNotIn('locationlat',row['history'][0])
  self.assertEqual(row['history'][0]['message'],'Signature required')
 def test_pagination_cache_pacing(self):
  with patch.object(m.urllib.request,'build_opener') as op:
   op.return_value.open.return_value=Response(json.dumps(DATA).encode())
   a=m.fetch_trackings({'limit':1},KEY); b=m.fetch_trackings({'limit':1},KEY)
   self.assertEqual(a['next_offset'],1); self.assertTrue(a['has_more']); self.assertTrue(b['cached'])
   self.assertEqual(op.return_value.open.call_count,1)
   with self.assertRaises(m.SafeError): m.fetch_trackings({'limit':2},KEY)
 def test_no_redirect(self):
  with self.assertRaises(m.SafeError): m.NoRedirect().redirect_request(None,None,302,'',{},'https://elsewhere.test')
 def test_error_does_not_leak_key(self):
  with patch.object(m.urllib.request,'build_opener') as op:
   op.return_value.open.side_effect=urllib.error.HTTPError(m.ENDPOINT+'?apikey='+KEY,403,KEY,{},None)
   with self.assertRaises(m.SafeError) as e: m.fetch_trackings({},KEY)
   self.assertNotIn(KEY,str(e.exception)); self.assertNotIn('apikey=',str(e.exception))
 def test_invalid_pagination_and_injection(self):
  for args in [{'limit':0},{'limit':True},{'offset':-1},{'url':'https://evil.test'},{'sortby':'apikey'}]:
   with self.assertRaises(m.SafeError): m.validated_params(args)
 def test_unexpected_shape_is_not_empty_success(self):
  with self.assertRaises(m.SafeError): m.normalize({'error':'bad'},'now')
 def test_redaction(self): self.assertEqual(m.redact({'note':KEY},KEY),{'note':'[redacted]'})
 def test_mcp_wire(self):
  messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-03-26'}},
  {'jsonrpc':'2.0','method':'notifications/initialized'},{'jsonrpc':'2.0','id':2,'method':'tools/list'}]
  result=subprocess.run([sys.executable,str(p),'serve'],input='\n'.join(map(json.dumps,messages))+'\n',text=True,capture_output=True,timeout=5)
  self.assertEqual(result.returncode,0); rows=[json.loads(x) for x in result.stdout.splitlines()]
  self.assertEqual(len(rows),2); self.assertEqual(rows[0]['result']['serverInfo']['name'],'shipshow-tracking')
if __name__=='__main__': unittest.main(verbosity=2)
