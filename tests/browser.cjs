const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const url=pathToFileURL(path.resolve(__dirname,'../examples/portrait-gaze-demo.html')).href;
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROME_CHANNEL?{channel:process.env.CHROME_CHANNEL}:{})});
 try{
 const context=await browser.newContext({viewport:{width:1280,height:900}});const page=await context.newPage();
 const errors=[],remote=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url());});
 await page.goto(url);const centers=await page.evaluate(()=>data.eyes.map(e=>e.center));
 const get=()=>page.locator('[data-iris]').evaluateAll(es=>es.map(e=>{const m=e.transform.baseVal.consolidate().matrix;return [m.e,m.f];}));
 await page.mouse.move(10,450);await page.waitForTimeout(600);let left=await get();assert.ok(left[0][0]<centers[0][0]-5);
 await page.mouse.move(1270,450);await page.waitForTimeout(600);let right=await get();assert.ok(right[0][0]>centers[0][0]+5);
 assert.ok(Math.abs((right[0][0]-centers[0][0])-(right[1][0]-centers[1][0]))<.001);
 if(process.env.PREVIEW_PATH)await page.screenshot({path:process.env.PREVIEW_PATH,fullPage:true});
 await page.locator('[data-toggle-motion]').click();await page.waitForTimeout(600);assert.ok(Math.abs((await get())[0][0]-centers[0][0])<.02);
 await page.locator('[data-toggle-motion]').click();await page.setViewportSize({width:820,height:700});await page.mouse.move(810,300);await page.waitForTimeout(600);assert.ok((await get())[0][0]>centers[0][0]);
 await page.emulateMedia({reducedMotion:'reduce'});await page.mouse.move(0,0);await page.waitForTimeout(200);assert.ok(Math.abs((await get())[0][0]-centers[0][0])<.02);
 await page.emulateMedia({reducedMotion:'no-preference'});await page.evaluate(()=>window.gazeDemo.destroy());await page.mouse.move(10,400);await page.waitForTimeout(100);assert.ok(Math.abs((await get())[0][0]-centers[0][0])<.02);
 const mobile=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:1});const phone=await mobile.newPage();await phone.goto(url);const client=await mobile.newCDPSession(phone);const box=await phone.locator('[data-gaze-portrait]').boundingBox();
 const xs=[box.x+box.width*.05,box.x+box.width*.95], y=box.y+box.height*.4;
 await client.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:xs[0],y}]});await phone.waitForTimeout(600);
 const touchX=()=>phone.locator('[data-iris]').first().evaluate(e=>e.transform.baseVal.consolidate().matrix.e);
 const touchLeft=await touchX();await client.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:xs[1],y}]});await phone.waitForTimeout(600);const touchRight=await touchX();assert.ok(touchRight-touchLeft>10);
 if(process.env.MOBILE_PREVIEW_PATH)await phone.screenshot({path:process.env.MOBILE_PREVIEW_PATH,fullPage:true});
 await client.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await phone.waitForTimeout(600);assert.ok(Math.abs(await touchX()-centers[0][0])<.02);
 assert.ok(await phone.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
 console.log(JSON.stringify({desktop:'left/right, paired offset, resize, pause, reduced motion, cleanup passed',touch:{left:touchLeft,right:touchRight,release:'neutral'},remoteRequests:remote.length,pageErrors:errors.length}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
