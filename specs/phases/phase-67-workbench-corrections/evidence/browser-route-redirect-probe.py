import asyncio, json, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urljoin, urlsplit
from playwright.async_api import async_playwright
hits=[]
servers=[]
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  index=servers.index(self.server)
  hits.append((index,self.path))
  if self.path in ('/chain','/direct'):
   dest=2 if self.path=='/direct' or index==1 else 1
   self.send_response(302); self.send_header('Location',f'http://127.0.0.1:{servers[dest].server_port}/chain' if dest==1 else f'http://127.0.0.1:{servers[dest].server_port}/exfil'); self.end_headers()
  else:
   self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers()
   self.wfile.write(f'<html><body><h1>Local app</h1><img src="http://127.0.0.1:{servers[2].server_port}/pixel"><script>fetch("http://127.0.0.1:{servers[2].server_port}/fetch").catch(()=>0); new WebSocket("ws://127.0.0.1:{servers[2].server_port}/socket");</script></body></html>'.encode())
 def log_message(self,*args):pass
for _ in range(3):servers.append(ThreadingHTTPServer(('127.0.0.1',0),Handler))
for s in servers:threading.Thread(target=s.serve_forever,daemon=True).start()
async def main():
 routed=[]; errors=[]; sockets=[]
 allowed={servers[0].server_port,servers[1].server_port}
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True)
  context=await browser.new_context(service_workers='block')
  async def route(r):
   u=r.request.url;routed.append(u)
   if urlsplit(u).port not in allowed:
    await r.abort('blockedbyclient');return
   response=await r.fetch(max_redirects=0)
   if 300<=response.status<400 and urlsplit(urljoin(u,response.headers.get('location',''))).port not in allowed:
    await r.abort('blockedbyclient');return
   await r.fulfill(response=response)
  await context.route('**/*',route)
  def socket(r):
   sockets.append(r.url)
   if urlsplit(r.url).port not in allowed:r.close(code=1008,reason='origin denied')
   else:r.connect_to_server()
  await context.route_web_socket('**/*',socket)
  page=await context.new_page()
  for path in ('/direct','/chain','/page'):
   try:await page.goto(f'http://127.0.0.1:{servers[0].server_port}{path}',timeout=5000)
   except Exception as e:errors.append(str(e).splitlines()[0])
  await asyncio.sleep(.2)
  snapshot=await page.locator('body').aria_snapshot()
  screenshot=await page.screenshot()
  await browser.close()
 print(json.dumps({'routed':routed,'hits':hits,'sockets':sockets,'errors':errors,'snapshot':snapshot,'image_bytes':len(screenshot),'blocked_hits':[h for h in hits if h[0]==2]},indent=2))
try:asyncio.run(main())
finally:
 for s in servers:s.shutdown();s.server_close()
