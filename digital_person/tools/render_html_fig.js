// 渲染 HTML 原理图 → PNG（deviceScaleFactor=1，截 .fig/.figure 元素）。
// 用法：node tools/render_html_fig.js <in.html> <out.png>
// A4 五号：body 60px；文档 {width=round(PNG宽/2880*100)%}。自检 nowrap 文本不溢出。
const { chromium } = require('/home/jiale/.npm/_npx/e41f203b7505f1fb/node_modules/playwright-core');
const path = require('path');
const CHROME = '/home/jiale/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome';
(async () => {
  const [htmlPath, outPath] = process.argv.slice(2);
  const browser = await chromium.launch({ executablePath: CHROME, headless: true });
  const page = await browser.newPage({ viewport: { width: 3200, height: 2200 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.resolve(htmlPath));
  await page.waitForTimeout(350);
  const over = await page.evaluate(() => {
    const bad = [];
    document.querySelectorAll('.nline,.lline,.nname,.lname,.nsub,.dline,.albl,.lbl,.pill,.cap,.math').forEach(el => {
      if (el.scrollWidth > el.clientWidth + 1) bad.push((el.textContent || '').trim().slice(0, 32));
    });
    return bad;
  });
  const fig = await page.$('.figure, .fig');
  const box = await fig.boundingBox();
  await fig.screenshot({ path: outPath });
  const w = Math.round(box.width), h = Math.round(box.height);
  console.log(`PNG ${w}x${h}  width%=${Math.min(100, Math.round(w / 2880 * 100))}  ${w <= 2880 ? 'OK' : 'TOO WIDE'}`);
  console.log(over.length ? ('OVERFLOW: ' + JSON.stringify(over)) : 'overflow: none');
  await browser.close();
})();
