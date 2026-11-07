// 界面基线 CSP-UI-1 浏览器实测：假数据跑完整流程 + 交互同步 + 手机宽度。
// 用法：python3 build.py && node test_page.js [--shots]   （需要 playwright 和 chromium）
// 有一条不过就以非 0 退出；--shots 时把基线截图写到 ../screenshots/（2 倍）。
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
const OUT = path.join(__dirname, 'out'), PAGE = 'file://' + path.join(OUT, 'index.html');
const SHOTS = process.argv.includes('--shots') ? path.join(__dirname, '..', 'screenshots') : null;
const fails = [], ok = [];
const expect = (cond, name, info) => { (cond ? ok : fails).push(name + (cond ? '' : ' → ' + (info || ''))); };
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: SHOTS ? 2 : 1 });
  const p = await ctx.newPage(); p.setDefaultTimeout(5000);
  await p.route('**/fonts.googleapis.com/**', r => r.abort());
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  const lede = () => p.textContent('.lede');
  const tab = () => p.textContent('.views [aria-selected="true"]');
  const onStage = () => p.evaluate(() => [...document.querySelectorAll('.stage')].findIndex(s => s.classList.contains('on')) + 1);
  const shot = async (n, fn) => { if (!SHOTS) return; if (fn) await fn(); await p.waitForTimeout(250); await p.evaluate(() => { const t = document.getElementById('toast'); if (t) t.classList.remove('on'); }); await p.waitForTimeout(260); await p.screenshot({ path: path.join(SHOTS, n) }); };
  const wait = (ms) => p.waitForTimeout(ms || 300);

  await p.goto(PAGE); await wait(800);
  expect((await lede()).includes('01E'), '打开停在 01E', await lede());
  expect((await tab()).trim().startsWith('段核心'), '默认页签是段核心', await tab());
  expect(await onStage() === 2, '描边在第 2 张阶段卡');
  await shot('01-mast.png', () => p.evaluate(() => window.scrollTo(0, 0)));
  for (const [k, i] of [['ep', 1], ['tables', 3], ['prompt', 4], ['seg', 2]]) {
    await p.click('.stage[data-view="' + k + '"]'); await wait(150);
    expect(await onStage() === i, '点阶段卡 ' + k + ' 描边跟着走');
  }
  await p.click('.views [data-view="tables"]'); await wait(150);
  expect(await onStage() === 3, '点页签 四张表 描边跟着走');
  await p.click('.views [data-view="seg"]'); await wait(150);
  await p.click('.jump a[data-to="seg-01E"]'); await wait();
  await shot('02-seg.png');
  expect(await p.locator('#seg-01E mark').count() === 1, '01E 的标注在句子里高亮');
  for (const c of ['01E', '01F', '01G']) { await p.click('#seg-' + c + ' [data-action="choose"][data-cand="A"]'); await wait(); }
  expect((await lede()).includes('连起来读'), '七段选完提示连读', await lede());
  for (let i = 0; i < 3; i++) { await p.click('.mast [data-action="run-next"]'); await wait(500); }
  expect((await tab()).trim().startsWith('四张表'), '跑完转到四张表');
  const chk = await p.textContent('#sec-check');
  expect(chk.includes('50–60') && chk.includes('照片'), '自动检查找出空拍和没去向的照片', chk.slice(0, 120));
  await shot('03-tables.png', () => p.click('.jump a[data-to="sec-test"]'));
  await shot('04-beats.png', () => p.click('.jump a[data-to="sec-beats"]'));
  const calls0 = await p.evaluate(() => (window.__calls || []).length);
  await p.click('#sec-check [data-fix="1"]'); await wait(600);
  const lastCall = await p.evaluate(() => (window.__calls || []).slice(-1)[0] || '');
  expect(await p.evaluate(() => (window.__calls || []).length) === calls0 + 1, '带漏洞重写四张表发了一次调用');
  await p.click('#sec-check [data-action="run"][data-node="n09"]'); await wait();
  await p.click('#sec-prop [data-action="decide"][data-v="drop"] >> nth=0'); await wait();
  await p.click('[data-action="decide-all"]'); await wait();
  expect((await lede()).includes('合好了'), '取舍完提示交给导演', await lede());
  await p.click('.views [data-view="prompt"]'); await wait();
  await p.click('[data-action="download"]'); await wait();
  expect(/剧情核心提示词-.*\.md$/.test(await p.evaluate(() => window.__saved || '')), '下载文件名');
  const prompt = await p.textContent('#promptOut');
  expect(prompt.startsWith('【剧情核心提示词】') && prompt.includes('交接：'), '提示词格式');
  expect(!prompt.includes('照片上他脸那块摸白了'), '删掉的提案不进提示词');
  await p.click('[data-action="copy"][data-what="director"]'); await wait();
  await shot('05-prompt.png', () => p.click('.jump a[data-to="sec-prompt"]'));
  fs.writeFileSync(path.join(OUT, 'state_full.json'), await p.evaluate(() => JSON.stringify(window.__store['projects/mengfusheng'])));
  await p.click('.views [data-view="seg"]'); await wait();
  await p.click('#seg-01E [data-action="reopen"]'); await wait();
  await p.click('#seg-01E [data-action="anno"][data-cand="B"]'); await p.fill('#seg-01E .annoForm [name=note]', '测试意见'); await p.click('#seg-01E .annoForm button[type="submit"]'); await wait();
  expect((await p.locator('#seg-01E .anno').count()) >= 2, '新标注存上');
  await p.fill('#seg-01E .composer textarea', '我自己写的核心'); await p.click('#seg-01E [data-action="own"]'); await wait();
  expect(await p.locator('#seg-01E .cand').count() === 4, '自己写的核心变成第 4 个候选');
  await p.fill('#seg-01E .composer textarea', '不要眼泪'); await p.click('#seg-01E .composer button[type="submit"]'); await wait(600);
  expect((await p.evaluate(() => (window.__calls || []).slice(-1)[0] || '')).length > 0, '按要求重新生成发了调用');
  expect((await lede()).includes('01E'), '重新生成后 01E 回到等你选', await lede());
  await p.click('details.vlog summary'); await wait();
  await p.click('details.vlog [data-action="restore-cp"] >> nth=1'); await wait(400);
  expect((await lede()).length > 0, '回到旧版本');
  expect(errs.length === 0, '页面没有报错', errs.join(' | '));

  const m = await b.newPage({ viewport: { width: 400, height: 900 }, deviceScaleFactor: SHOTS ? 2 : 1 });
  await m.route('**/fonts.googleapis.com/**', r => r.abort());
  await m.goto(PAGE); await m.waitForTimeout(800);
  if (SHOTS) await m.screenshot({ path: path.join(SHOTS, '06-mobile.png') });
  for (const v of ['seg', 'ep', 'tables', 'prompt']) {
    await m.click('.views [data-view="' + v + '"]'); await m.waitForTimeout(200);
    const w = await m.evaluate(() => document.documentElement.scrollWidth);
    expect(w <= 400, '手机 400 宽不横向滚动：' + v, String(w));
  }
  await b.close();
  console.log('通过 ' + ok.length + ' 条');
  if (fails.length) { console.log('不过 ' + fails.length + ' 条：\n- ' + fails.join('\n- ')); process.exit(1); }
  console.log('全部通过');
})();
