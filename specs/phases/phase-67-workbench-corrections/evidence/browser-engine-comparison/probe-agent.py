import asyncio,json,os,tempfile,time
from pathlib import Path
from playwright.async_api import async_playwright
from shadow_hdk.runtime.processes import start_held,stop_or_kill

BINARY='/tmp/hdk67-browser-evaluation/agent-browser-package/package/bin/agent-browser-darwin-arm64'
async def main():
 with tempfile.TemporaryDirectory(dir='/tmp',prefix='ab-eval-') as d:
  path=Path(d)
  async with async_playwright() as p:
   context=await p.chromium.launch_persistent_context(path/'chrome',headless=True,executable_path=p.chromium.executable_path,args=['--remote-debugging-port=0'],service_workers='block',accept_downloads=False)
   page=context.pages[0]
   await page.set_content('<h1>Local fixture</h1><input aria-label="Title"><button onclick="document.querySelector(\'h1\').textContent=\'Clicked\'">Save</button>')
   port,ws=(path/'chrome/DevToolsActivePort').read_text().splitlines()
   env={'PATH':os.environ['PATH'],'HOME':d,'AGENT_BROWSER_DAEMON':'1','AGENT_BROWSER_SOCKET_DIR':d,'AGENT_BROWSER_SESSION':'owned','AGENT_BROWSER_NO_WEBMCP':'1'}
   proc=await start_held(BINARY,env=env,cwd=d,stdin=asyncio.subprocess.DEVNULL)
   async def rpc(action,**params):
    reader,writer=await asyncio.open_unix_connection(str(path/'owned.sock'))
    writer.write((json.dumps({'id':'1','action':action,**params})+'\n').encode());await writer.drain()
    result=json.loads(await asyncio.wait_for(reader.readline(),30));writer.close();await writer.wait_closed()
    print(action,json.dumps(result)[:450]);return result
   try:
    for _ in range(100):
     if (path/'owned.sock').exists():break
     await asyncio.sleep(.02)
    await rpc('launch',cdpUrl=f'http://127.0.0.1:{port}',webmcp=False,plugins=[])
    snap=await rpc('snapshot')
    refs=snap['data']['refs'];ref=next(k for k,v in refs.items() if v['role']=='textbox')
    await rpc('fill',selector='@'+ref,value='Typed')
    await rpc('snapshot')
    await rpc('tab_list')
    await rpc('screenshot',path=str(path/'shot.png'))
    print('VALUE',await page.locator('input').input_value(),'SCREENSHOT',(path/'shot.png').stat().st_size)
   finally:
    await stop_or_kill(proc,grace_s=3)
    await context.close()
asyncio.run(main())
