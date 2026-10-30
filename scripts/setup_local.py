#!/usr/bin/env python3
"""One-use, loopback-only credential entry. No external page assets or request logging."""
import html
import json
import secrets
import sys
import time
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
import shipshow

TOKEN=secrets.token_urlsafe(32)
DONE=False
SETUP_WINDOW_SECONDS=8*60*60
PAGE='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Connect ShipShow</title><style>body{font:17px system-ui;background:#f5f6f8;color:#17202c;margin:0;padding:50px 22px}main{max-width:560px;margin:auto;background:white;padding:36px;border-radius:18px;box-shadow:0 8px 40px #18203012}h1{margin-top:0;font-size:29px}p{line-height:1.6;color:#465366}label{display:block;font-weight:650;margin-top:24px}input{width:100%;box-sizing:border-box;padding:14px;border:1px solid #bcc6d4;border-radius:8px;margin:10px 0 18px;font-size:17px}button{background:#284e77;color:white;border:0;border-radius:8px;padding:14px 20px;font-size:17px;cursor:pointer}.small{font-size:14px}.error{color:#a12626}</style></head><body><main><h1>Connect ShipShow</h1><p>Use your existing ShipShow API key to read packages, arrival estimates and delivery updates.</p><p class="small">This page runs only on this Mac. The key is sent directly to ShipShow to verify access, then saved in macOS Keychain. It is not placed in chat or plugin files.</p>{message}<form method="post"><input type="hidden" name="token" value="{token}"><label for="key">ShipShow API key</label><input id="key" name="key" type="password" autocomplete="off" required autofocus><button type="submit">Save key and verify connection</button></form><p class="small">Requires your existing ShipShow Pro subscription. This plugin only reads; it does not change packages or turn on background monitoring.</p></main></body></html>'''

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def respond(self,status,body):
        raw=body.encode()
        self.send_response(status)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers(); self.wfile.write(raw)
    def allowed(self):
        return self.headers.get('Host')==self.server.allowed_host and self.path=='/'+TOKEN
    def page(self,message=''):
        return PAGE.replace('{token}',TOKEN).replace('{message}',message)
    def do_GET(self):
        if not self.allowed(): self.respond(404,'Not found'); return
        self.respond(200,self.page())
    def do_POST(self):
        global DONE
        if not self.allowed():
            self.respond(403,'This setup link is no longer valid. Reopen the current local setup page.'); return
        # Sandboxed webviews may use an opaque (null) or missing Origin.
        # The private URL and 256-bit synchronizer token remain mandatory.
        origin=self.headers.get('Origin')
        if origin not in (None, 'null', 'http://'+self.server.allowed_host):
            print(json.dumps({'setup_error':'unexpected_origin','origin':origin[:200]}),flush=True)
            self.respond(403,'This browser is submitting from a different origin. Please reopen the local setup page in its own tab.'); return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<1 or size>4096: raise ValueError()
            fields=urllib.parse.parse_qs(self.rfile.read(size).decode())
            if not secrets.compare_digest(fields.get('token',[''])[0],TOKEN):
                self.respond(403,'The setup token is missing or expired. Reload the current setup page.'); return
            key=fields.get('key',[''])[0].strip(); uuid.UUID(key)
        except (ValueError,UnicodeError):
            self.respond(400,self.page('<p class="error">Enter the UUID API key shown in ShipShow.</p>')); return
        try:
            result=shipshow.fetch_trackings({'limit':1},supplied_key=key)
            shipshow.save_key(key)
        except shipshow.SafeError as e:
            self.respond(400,self.page('<p class="error">'+html.escape(str(e))+'</p>')); return
        except Exception:
            self.respond(500,self.page('<p class="error">Setup could not finish. No credential was logged.</p>')); return
        self.respond(200,'<!doctype html><title>ShipShow connected</title><h1>ShipShow connected</h1><p>Your API key is verified and saved in macOS Keychain. You can close this page.</p>')
        print(json.dumps({'configured':True,'api_verified':True,'sample_count':len(result['trackings']),'has_more':result['has_more']}),flush=True)
        DONE=True

def run(port=0, timeout_seconds=SETUP_WINDOW_SECONDS):
    global DONE
    DONE=False
    server=HTTPServer(('127.0.0.1',port),Handler)
    server.allowed_host='127.0.0.1:'+str(server.server_port)
    server.timeout=1
    print('SETUP_URL=http://'+server.allowed_host+'/'+TOKEN,flush=True)
    deadline=time.monotonic()+timeout_seconds
    try:
        while not DONE and time.monotonic()<deadline:
            server.handle_request()
    finally:
        server.server_close()
    if not DONE: print('Setup window expired without saving a key.',flush=True)

if __name__=='__main__':
    run()
