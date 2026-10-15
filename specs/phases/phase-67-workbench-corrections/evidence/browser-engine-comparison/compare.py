import asyncio,json,os,tempfile,time,statistics,threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from playwright.async_api import async_playwright
import psutil
from shadow_hdk.runtime.processes import start_held,stop_or_kill
ROOT=Path('/tmp/hdk67-browser-evaluation')
class App(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(b'<h1>Fixture</h1><label>Title<input aria-label="Title"></label><button onclick="document.querySelector(\'h1\').textContent=\'Clicked\'">Save</button><select aria-label="Choice"><option value="a">A</option><option value="b">B</option></select>')
async def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),App);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start();url=f'http://127.0.0.1:{server.server_port}'
 results={}
 try:
  for engine in ('playwright','agent-browser','browser-use','browse'):
   with tempfile.TemporaryDirectory(dir='/tmp',prefix='be-') as d:
    path=Path(d)
    async with async_playwright() as p:
     context=await p.chromium.launch_persistent_context(path/'chrome',headless=True,executable_path=p.chromium.executable_path,args=['--remote-debugging-port=0'],service_workers='block',accept_downloads=False)
     page=context.pages[0];await page.goto(url)
     port,ws= (path/'chrome/DevToolsActivePort').read_text().splitlines();endpoint=f'http://127.0.0.1:{port}'
     env={'PATH':os.environ['PATH'],'HOME':d,'TMPDIR':d,'LANG':'en_US.UTF-8'}
     proc=None;t0=time.perf_counter()
     try:
      if engine=='playwright':
       await page.get_by_role('textbox').fill('Playwright');await page.get_by_role('button').click();text=await page.locator('body').aria_snapshot();assert 'Clicked' in text
       samples=[]
       for _ in range(10):
        t=time.perf_counter();await page.locator('body').aria_snapshot();samples.append(time.perf_counter()-t)
       results[engine]={'snapshot_median_s':statistics.median(samples),'snapshot_bytes':len(text.encode()),'adapter_runtime':'Playwright driver + shared Chromium','element_refs':False}
      elif engine=='browser-use':
       env.update(ANONYMIZED_TELEMETRY='false',BROWSER_USE_DISABLE_EXTENSIONS='1',BROWSER_USE_CONFIG_DIR=d,BROWSER_USE_LOGGING_LEVEL='error')
       proc=await start_held(str(ROOT/'browser-use-env/bin/python'),str(ROOT/'browser-use-direct.py'),endpoint,d,url,env=env,cwd=d,stdin=asyncio.subprocess.DEVNULL)
       output,error=await asyncio.wait_for(proc.communicate(),60)
       if proc.returncode:results[engine]={'error':error.decode()[-2500:],'output_tail':output.decode()[-1500:]}
       else:
        payload=json.loads(next(l[7:] for l in output.decode().splitlines() if l.startswith('RESULT ')));results[engine]=payload
      else:
       if engine=='agent-browser':
        env.update(AGENT_BROWSER_DAEMON='1',AGENT_BROWSER_SOCKET_DIR=d,AGENT_BROWSER_SESSION='owned',AGENT_BROWSER_NO_WEBMCP='1')
        proc=await start_held(str(ROOT/'agent-browser-package/package/bin/agent-browser-darwin-arm64'),env=env,cwd=d,stdin=asyncio.subprocess.DEVNULL)
       else:
        env['BROWSE_DAEMON_DIR']=d
        proc=await start_held('node',str(ROOT/'browse-direct.mjs'),f'ws://127.0.0.1:{port}{ws}',env=env,cwd=d,stdin=asyncio.subprocess.DEVNULL)
       for _ in range(150):
        if (path/'owned.sock').exists():break
        if proc.returncode is not None:raise RuntimeError('daemon exited')
        await asyncio.sleep(.02)
       async def rpc(action,**kw):
        message=({'id':'fixture','action':action,**kw} if engine=='agent-browser' else {'id':'fixture','type':'command','command':action,'params':kw})
        reader,writer=await asyncio.open_unix_connection(str(path/'owned.sock'));writer.write((json.dumps(message)+'\n').encode());await writer.drain();result=json.loads(await asyncio.wait_for(reader.readline(),40));writer.close();await writer.wait_closed()
        if result.get('success') is False or result.get('type')=='error':raise RuntimeError(result)
        return result['data']
       if engine=='agent-browser':await rpc('launch',cdpUrl=endpoint,webmcp=False,plugins=[])
       else: await rpc('open',url=url,waitUntil='domcontentloaded')
       await rpc('snapshot')
       await rpc('fill',selector='input',value=engine);await rpc('click',selector='button')
       snap=await rpc('snapshot');text=snap.get('snapshot',snap.get('tree',''));assert 'Clicked' in text
       if engine=='browse':await rpc('screenshot',path=str(path/'shot.png'))
       else:await rpc('screenshot',path=str(path/'shot.png'))
       samples=[];before=psutil.Process(proc.pid).cpu_times()
       for _ in range(10):
        t=time.perf_counter();await rpc('snapshot');samples.append(time.perf_counter()-t)
       own=psutil.Process(proc.pid);after=own.cpu_times();cpu=after.user+after.system-before.user-before.system
       results[engine]={'startup_and_interaction_s':time.perf_counter()-t0,'snapshot_median_s':statistics.median(samples),'snapshot_bytes':len(text.encode()),'daemon_rss_bytes':own.memory_info().rss,'daemon_cpu_s_10_snapshots':cpu,'screenshot':(path/'shot.png').is_file(),'refs':len(snap.get('refs',{})) if engine=='agent-browser' else '@' in text}
     except Exception as error:results[engine]={'error':type(error).__name__+': '+str(error)}
     finally:
      if proc:await stop_or_kill(proc,grace_s=3)
      await context.close()
  print(json.dumps(results,indent=2));(ROOT/'comparison.json').write_text(json.dumps(results,indent=2))
 finally:
  server.shutdown();server.server_close();worker.join()
asyncio.run(main())
