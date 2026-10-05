const puppeteer = (() => {
  try { return require('puppeteer-core'); }
  catch { /* fall through to alternate locations */ }
  try { return require('/tmp/opencode/pptr/node_modules/puppeteer-core'); }
  catch { return null; }
})();

(async () => {
  if (!puppeteer) {
    console.log(JSON.stringify({ status: 'SKIP', reason: 'puppeteer-core not installed' }));
    process.exit(2);
  }
  const [htmlPath, shotDir] = process.argv.slice(2);
  if (!htmlPath) {
    console.log(JSON.stringify({ status: 'ERROR', reason: 'usage: verify-hover.js <html> <shotdir>' }));
    process.exit(1);
  }
  const fs = require('fs');
  const path = require('path');
  const out = shotDir || '/tmp/opencode';
  fs.mkdirSync(out, { recursive: true });

  const candidates = [
    process.env.CHROMIUM_PATH,
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
  ].filter(Boolean);
  const executablePath = candidates.find(p => { try { return fs.existsSync(p); } catch { return false; } });
  if (!executablePath) {
    console.log(JSON.stringify({ status: 'SKIP', reason: 'no chromium binary found' }));
    process.exit(2);
  }

  const browser = await puppeteer.launch({
    executablePath, headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--allow-file-access-from-files'],
  });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1600, height: 900 });
    const errors = [];
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    page.on('pageerror', e => errors.push('pageerror: ' + e.message));
    await page.goto('file://' + htmlPath, { waitUntil: 'networkidle0', timeout: 30000 });
    await new Promise(r => setTimeout(r, 2500)); // MathJax + viewer init

    const sections = await page.evaluate(() => ({
      n: document.querySelectorAll('.content-section').length,
      kinds: Object.fromEntries([...document.querySelectorAll('.content-section')]
        .map(el => el.dataset.kind || 'none').map(k => [k, 0])
        .concat([...document.querySelectorAll('.content-section')].map(el => [el.dataset.kind || 'none', 1]))
        .reduce((m, [k, v]) => m.set(k, (m.get(k) || 0) + v), new Map()).entries()),
    }));
    await page.screenshot({ path: path.join(out, 'verify-init.png') });

    // Hover a sample: first section, first ref section, one section per
    // distinct viewer page — enough to prove sync without N screenshots.
    const plan = await page.evaluate(() => {
      const els = [...document.querySelectorAll('.content-section')];
      const first = 0;
      const firstRef = els.findIndex(el => el.dataset.side === 'ref');
      const pages = [];
      const seen = new Set();
      els.forEach((el, i) => {
        const key = (el.dataset.base || el.dataset.src || '') + '|' + (el.dataset.page || '');
        if (!seen.has(key)) { seen.add(key); pages.push(i); }
      });
      return [...new Set([first, firstRef, ...pages.slice(0, 6)])].filter(i => i >= 0);
    });

    const hovers = [];
    for (const idx of plan) {
      await page.evaluate((i) => {
        const els = document.querySelectorAll('.content-section');
        const el = els[i];
        if (el) {
          el.scrollIntoView({ block: 'center' });
          el.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
        }
      }, idx);
      await new Promise(r => setTimeout(r, 500));
      const st = await page.evaluate(() => ({
        img: (document.getElementById('viewer-img').src || '').split('/').slice(-2).join('/'),
        imgVisible: document.getElementById('viewer-img').style.display !== 'none',
        box: document.getElementById('box-overlay').style.display,
        chip: document.getElementById('ref-viewer-text').textContent.slice(0, 100),
        pageLabel: document.getElementById('page-label').textContent,
      }));
      hovers.push({ idx, ...st });
      await page.screenshot({ path: path.join(out, `verify-hover-${idx}.png`) });
    }

    console.log(JSON.stringify({
      status: errors.length ? 'WARN' : 'OK',
      sections: sections.n, kinds: sections.kinds,
      hovers, consoleErrors: errors.slice(0, 5),
      shots: out,
    }, null, 1));
  } finally {
    await browser.close();
  }
})().catch(e => {
  console.log(JSON.stringify({ status: 'ERROR', reason: String(e && e.message || e) }));
  process.exit(1);
});
