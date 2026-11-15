const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { spawn } = require('child_process');
const { pathToFileURL } = require('url');

(async function () {
  const output = path.resolve('store/preview');
  const profile = fs.mkdtempSync(path.join(output, 'page-tools-browser-'));
  const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', [
    '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--disable-background-networking', '--disable-component-update', '--disable-extensions',
    '--remote-debugging-port=0', '--user-data-dir=' + profile,
    '--host-resolver-rules=MAP * ~NOTFOUND', 'about:blank'
  ], { stdio: 'ignore', windowsHide: true, env: { ...process.env, TEMP: output, TMP: output } });
  let socket;
  let id = 0;
  const waiting = new Map();
  try {
    let port;
    for (let attempt = 0; attempt < 60; attempt++) {
      try { port = Number(fs.readFileSync(path.join(profile, 'DevToolsActivePort'), 'utf8').split('\n')[0]); break; }
      catch (error) { await new Promise(resolve => setTimeout(resolve, 100)); }
    }
    assert(port, 'The isolated browser must start');
    const tab = await (await fetch('http://127.0.0.1:' + port + '/json/new?about:blank', { method: 'PUT' })).json();
    socket = new WebSocket(tab.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener('open', resolve, { once: true });
      socket.addEventListener('error', reject, { once: true });
    });
    socket.addEventListener('message', event => {
      const message = JSON.parse(event.data);
      const item = waiting.get(message.id);
      if (!item) return;
      waiting.delete(message.id);
      clearTimeout(item.timer);
      message.error ? item.reject(Error(message.error.message)) : item.resolve(message.result);
    });
    const rpc = (method, params = {}) => new Promise((resolve, reject) => {
      const next = ++id;
      const timer = setTimeout(() => { waiting.delete(next); reject(Error('Timed out: ' + method)); }, 10000);
      waiting.set(next, { resolve, reject, timer });
      socket.send(JSON.stringify({ id: next, method, params }));
    });
    const evaluate = async expression => {
      const result = await rpc('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
      if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails));
      return result.result.value;
    };
    const until = async expression => {
      for (let attempt = 0; attempt < 100; attempt++) {
        if (await evaluate(expression)) return;
        await new Promise(resolve => setTimeout(resolve, 60));
      }
      throw Error('Condition not reached: ' + expression);
    };
    const load = async name => {
      await rpc('Page.navigate', { url: pathToFileURL(path.join(output, name)).href });
      await until('location.pathname.endsWith(' + JSON.stringify(name) + ') && document.readyState === "complete" && !!document.getElementById("back-to-top")');
      await evaluate('(()=>{const style=document.createElement("style");style.textContent=' + JSON.stringify(fs.readFileSync(path.resolve('store/static/shared/css/mobile-layout.css'), 'utf8')) + ';document.head.appendChild(style)})()');
      await evaluate('window.scrollTo({top:0,behavior:"instant"})');
      await until('window.scrollY === 0');
    };
    const size = (width, height = 900) => rpc('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
    const screenshot = async name => {
      const result = await rpc('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
      fs.writeFileSync(path.join(output, name), Buffer.from(result.data, 'base64'));
    };
    const buttonVisible = 'getComputedStyle(document.getElementById("back-to-top")).visibility === "visible"';
    const shopSpace = 'Math.abs(parseFloat(getComputedStyle(document.body).paddingTop) - document.querySelector(".navbar.fixed-top").offsetHeight) < 1';
    const pageBelowNav = 'document.querySelector(".navbar.fixed-top").nextElementSibling.getBoundingClientRect().top >= document.querySelector(".navbar.fixed-top").getBoundingClientRect().bottom - 1';
    const checks = [];
    const shopMetrics = [];
    await rpc('Page.enable');
    await size(1366);
    await load('page-tools-landing.html');
    assert.equal(await evaluate('document.querySelectorAll("#back-to-top").length'), 1);
    assert.equal(await evaluate(buttonVisible), false);
    await evaluate('window.scrollTo(0,200)');
    assert.equal(await evaluate(buttonVisible), false);
    await evaluate('window.scrollTo(0,650)');
    await until(buttonVisible);
    assert.equal(await evaluate('document.getElementById("back-to-top").getAttribute("aria-label")'), 'Back to top');
    await evaluate('new Promise(resolve=>setTimeout(resolve,220))');
    await screenshot('page-tools-desktop.png');
    await evaluate('document.getElementById("back-to-top").click()');
    await until('window.scrollY === 0');
    await until('!(' + buttonVisible + ')');
    checks.push('hidden at top and below threshold', 'appears after 300px', 'smooth click returns to top', 'single accessible button');

    await rpc('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
    await evaluate('window.scrollTo(0,650)');
    await until(buttonVisible);
    await evaluate('window.__originalScrollTo=window.scrollTo.bind(window);window.scrollTo=function(options){window.__scrollOptions=options;window.__originalScrollTo(options)};document.getElementById("back-to-top").click()');
    assert.equal(await evaluate('window.__scrollOptions.behavior'), 'auto');
    await until('window.scrollY === 0');
    assert.equal(await evaluate('getComputedStyle(document.getElementById("back-to-top")).transitionDuration'), '0s');
    checks.push('reduced motion preference');
    await rpc('Emulation.setEmulatedMedia', { features: [] });

    await size(390, 844);
    await evaluate('document.documentElement.dataset.display="night";window.__originalScrollTo(0,650)');
    await until(buttonVisible);
    await evaluate('new Promise(resolve=>setTimeout(resolve,220))');
    const button = await evaluate('(()=>{const r=document.getElementById("back-to-top").getBoundingClientRect();return {left:r.left,right:r.right,bottom:r.bottom,width:r.width,viewport:innerWidth}})()');
    assert(button.left >= 0 && button.right <= button.viewport && button.bottom <= 844);
    assert.equal(button.width, 44);
    await screenshot('page-tools-mobile-night.png');
    checks.push('mobile button placement', 'night mode');

    await load('page-tools-landing.html');
    for (const width of [320, 360, 390, 430, 480, 600, 768, 900, 1024, 1280, 1366, 1440, 1920, 2560]) {
      await size(width, width < 576 ? 844 : 900);
      await until('document.documentElement.scrollWidth <= innerWidth');
      const controlBounds = await evaluate('(()=>{const r=document.getElementById("back-to-top").getBoundingClientRect();return r.left >= 0 && r.right <= innerWidth && r.bottom <= innerHeight})()');
      assert(controlBounds, 'Back-to-top button must stay inside the viewport at ' + width + 'px');
    }
    checks.push('landing page avoids horizontal overflow from 320px to desktop');

    await size(1366);
    await load('page-tools-shop.html');
    await until(shopSpace);
    assert(await evaluate(pageBelowNav));
    await screenshot('page-tools-shop-desktop.png');
    for (const width of [320, 360, 390, 768, 1024, 1366]) {
      await size(width, 844);
      await until(shopSpace);
      assert(await evaluate(pageBelowNav));
      const collapsed = await evaluate('document.querySelector(".navbar.fixed-top").offsetHeight');
      let expanded = collapsed;
      if (width < 992) {
        await evaluate('document.getElementById("navbarSupportedContent").classList.add("show")');
        await until('document.querySelector(".navbar.fixed-top").offsetHeight > ' + collapsed);
        await until(shopSpace);
        assert(await evaluate(pageBelowNav));
        expanded = await evaluate('document.querySelector(".navbar.fixed-top").offsetHeight');
        await evaluate('document.getElementById("navbarSupportedContent").classList.remove("show")');
        await until(shopSpace);
        assert(await evaluate(pageBelowNav));
      }
      shopMetrics.push({ width, collapsed, expanded });
      if (width === 390) await screenshot('page-tools-shop-mobile.png');
    }
    checks.push('fixed shop navbar spacing', 'responsive shop spacing', 'mobile menu expansion and collapse');

    await size(1366);
    await load('page-tools-shop-about.html');
    await until(shopSpace);
    assert(await evaluate(pageBelowNav));
    assert(await evaluate('document.querySelector(".jumbotron").textContent.includes("sports essentials")'));
    assert.equal(await evaluate('/lorem|ipsum|Donec|Vivamus/i.test(document.body.textContent)'), false);
    await screenshot('page-tools-shop-about.png');
    checks.push('shop background section visible below navbar', 'concise replacement copy');

    await load('page-tools-product.html');
    assert.equal(await evaluate('parseFloat(getComputedStyle(document.body).paddingTop)'), 0);
    assert.equal(await evaluate('getComputedStyle(document.querySelector(".mac-navbar")).position'), 'sticky');
    await evaluate('window.scrollTo(0,650)');
    await until(buttonVisible);
    checks.push('product page button and existing sticky navbar');

    await load('page-tools-blog.html');
    assert.equal(await evaluate('document.querySelectorAll("#back-to-top").length'), 1);
    assert.equal(await evaluate(buttonVisible), false);
    checks.push('blog page shared button');

    const layoutFailures = [];
    for (const page of ['page-tools-landing.html', 'page-tools-shop.html', 'page-tools-product.html', 'page-tools-shop-about.html', 'page-tools-blog.html']) {
      await load(page);
      for (const width of [320, 360, 390, 600, 768, 900, 1024, 1366, 1920]) {
        await size(width, 844);
        const overflow = await evaluate('document.documentElement.scrollWidth > innerWidth');
        if (overflow) layoutFailures.push({page,width, elements:await evaluate('Array.from(document.body.querySelectorAll("*")).filter(e=>{const r=e.getBoundingClientRect();return r.width>0 && r.right>innerWidth+1}).slice(0,8).map(e=>e.className)')});
        if(width===390) await screenshot('responsive-' + page.replace('.html','.png'));
      }
    }
    assert.deepEqual(layoutFailures, [], JSON.stringify(layoutFailures));
    checks.push('five page layouts at nine mobile, tablet and desktop widths');
    await load('page-tools-landing.html');
    await size(390, 844);
    await evaluate('window.scrollTo(0,650)');
    await until('Math.abs(document.querySelector("body > header").getBoundingClientRect().top) < 1');
    assert(await evaluate('(()=>{const a=document.querySelector(".store-search-trigger").getBoundingClientRect(),b=document.querySelector(".openbtn").getBoundingClientRect();return Math.abs(a.top+a.height/2-b.top-b.height/2)<2})()'));
    await evaluate('document.body.insertAdjacentHTML("beforeend",' + JSON.stringify(fs.readFileSync(path.resolve('store/templates/store/includes/club_map.html'), 'utf8')) + ')');
    await evaluate('(()=>{const a=document.createElement("a");a.setAttribute("data-club-map","");a.href="#";a.id="test-map-trigger";document.body.appendChild(a)})()');
    await evaluate(fs.readFileSync(path.resolve('store/static/shared/js/club-map.js'), 'utf8'));
    await evaluate('document.getElementById("test-map-trigger").click()');
    assert(await evaluate('document.getElementById("club-map").open'));
    await evaluate('document.getElementById("club-map-address").value="Test Club & Sports";document.querySelector(".club-map-form").dispatchEvent(new Event("submit",{bubbles:true,cancelable:true}))');
    assert(await evaluate('new URL(document.querySelector(".club-map-frame").src).searchParams.get("q") === "Test Club & Sports"'));
    await evaluate('document.querySelector(".club-map-close").click()');
    assert(await evaluate('!document.getElementById("club-map").open'));
    await load('page-tools-shop.html');
    await size(390,844);
    assert(await evaluate('(()=>{const c=document.querySelectorAll(".carousel-item.active .card");return c[1].getBoundingClientRect().top-c[0].getBoundingClientRect().bottom>=24})()'));
    checks.push('sticky club header', 'header control alignment', '24px vertical product gap', 'map dialog and encoded location URL (external map requests blocked in preview)');
    const report = { result: 'PASS', checks, shopMetrics, local_previews_only: true };
    fs.writeFileSync(path.join(output, 'page-tools-browser-checks.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
    await rpc('Browser.close').catch(() => {});
  } finally {
    if (socket) socket.close();
    chrome.kill();
  }
})().catch(error => {
  fs.writeFileSync(path.resolve('store/preview/page-tools-browser-checks.json'), JSON.stringify({ result: 'FAIL', error: error.stack }, null, 2));
  console.error(error);
  process.exitCode = 1;
});
