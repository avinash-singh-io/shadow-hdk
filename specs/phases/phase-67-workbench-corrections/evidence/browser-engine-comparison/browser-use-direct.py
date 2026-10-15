import asyncio,json,sys,time,resource
from browser_use.browser.session import BrowserSession

async def main():
 browser=BrowserSession(cdp_url=sys.argv[1],is_local=True,headless=True,enable_default_extensions=False,keep_alive=True,user_data_dir=sys.argv[2])
 await browser.start()
 page=await browser.get_current_page()
 assert page is not None
 await page.goto(sys.argv[3])
 await asyncio.sleep(.15)
 elements=await page.get_elements_by_css_selector('input')
 await elements[0].fill('Browser Use direct')
 button=(await page.get_elements_by_css_selector('button'))[0]
 await button.click()
 state=await browser.get_browser_state_summary(include_screenshot=True)
 text=state.dom_state.llm_representation()
 assert 'Clicked' in text
 assert state.screenshot and state.dom_state.selector_map
 screenshot=bool(state.screenshot)
 samples=[]
 for _ in range(10):
  t=time.perf_counter();state=await browser.get_browser_state_summary(include_screenshot=False,cached=False);samples.append(time.perf_counter()-t)
 print('RESULT '+json.dumps({'snapshots_s':samples,'snapshot_bytes':len(text.encode()),'refs':len(state.dom_state.selector_map),'screenshot':screenshot,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'process_cpu_s':resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime}),flush=True)
 await browser.kill()
asyncio.run(main())
