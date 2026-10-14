#!/usr/bin/env node
// 本地 HTML 的确定性辅助渲染；不包含任何 App 的固定视觉模板。
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';

const [projectArg, batchArg] = process.argv.slice(2);
const sha = data => createHash('sha256').update(data).digest('hex');
const exists = async p => { try { await fs.access(p); return true; } catch { return false; } };

function crc32(data) {
  let value = 0xffffffff;
  for (const byte of data) {
    value ^= byte;
    for (let bit = 0; bit < 8; bit++) value = (value >>> 1) ^ ((value & 1) ? 0xedb88320 : 0);
  }
  return (value ^ 0xffffffff) >>> 0;
}

function srgbPng(data) {
  if (data.subarray(0, 8).toString('hex') !== '89504e470d0a1a0a' || data[24] !== 8 || data[25] !== 2) {
    throw new Error('需要不透明 RGB8 PNG；检查页面背景和渲染器');
  }
  let offset = 8;
  while (offset < data.length) {
    const length = data.readUInt32BE(offset);
    const type = data.toString('ascii', offset + 4, offset + 8);
    if (type === 'sRGB') return data;
    if (type === 'iCCP') throw new Error('输入已经有 ICC，不能未经核对叠加 sRGB 标记');
    offset += length + 12;
  }
  const chunk = Buffer.alloc(13);
  chunk.writeUInt32BE(1, 0); chunk.write('sRGB', 4); chunk[8] = 0;
  chunk.writeUInt32BE(crc32(chunk.subarray(4, 9)), 9);
  // IHDR 之后加入 sRGB 标记，不改变或重新采样像素。
  return Buffer.concat([data.subarray(0, 33), chunk, data.subarray(33)]);
}

async function main() {
  if (!projectArg || !batchArg) throw new Error('用法: node scripts/render.mjs <项目根目录> <批次相对路径>');
  const root = await fs.realpath(path.resolve(projectArg));
  async function local(name, output = false) {
    if (typeof name !== 'string' || !name || path.isAbsolute(name)) throw new Error('需要项目相对路径');
    const result = path.resolve(root, name);
    const rel = path.relative(root, result);
    if (!rel || rel.startsWith('..' + path.sep) || rel === '..') throw new Error('路径超出项目或指向根目录');
    if (output && rel.split(path.sep).includes('baselines')) throw new Error('不能写入已确认基准目录');
    // 同时检查现有父目录，防止符号链接把写入导向项目外。
    let parent = result;
    while (!(await exists(parent))) parent = path.dirname(parent);
    const actual = await fs.realpath(parent);
    if (actual !== root && !actual.startsWith(root + path.sep)) throw new Error('符号链接超出项目目录');
    return result;
  }
  const batch = JSON.parse(await fs.readFile(await local(batchArg), 'utf8'));
  if (!Array.isArray(batch.jobs) || !batch.jobs.length) throw new Error('批次没有 jobs');
  const reportPath = await local(batch.report, true);
  if (await exists(reportPath)) throw new Error('报告已存在，拒绝覆盖');
  const ids = new Set(), outputs = new Set();
  for (const job of batch.jobs) {
    if (!job.id || ids.has(job.id)) throw new Error('任务 ID 缺失或重复');
    ids.add(job.id);
    for (const key of ['width', 'height']) if (!Number.isInteger(job[key]) || job[key] <= 0) throw new Error('画布尺寸需要正整数');
    if (job.dpr !== undefined && (!Number.isFinite(job.dpr) || job.dpr <= 0)) throw new Error('无效 DPR');
    if (job.safe_rect && (job.safe_rect.length !== 4 || job.safe_rect.some(v => !Number.isFinite(v)) ||
        job.safe_rect[0] < 0 || job.safe_rect[1] < 0 || job.safe_rect[2] <= 0 || job.safe_rect[3] <= 0 ||
        job.safe_rect[0]+job.safe_rect[2] > job.width || job.safe_rect[1]+job.safe_rect[3] > job.height)) {
      throw new Error('无效 safe_rect');
    }
    const target = await local(job.output, true);
    if (outputs.has(target) || target === reportPath || await exists(target)) throw new Error('输出重复或已存在: ' + job.output);
    outputs.add(target);
    await fs.access(await local(job.html));
  }
  const specifier = process.env.ASC_PLAYWRIGHT_MODULE;
  const module = specifier ? await import(pathToFileURL(path.resolve(specifier)).href) : await import('playwright');
  const playwright = module.chromium ? module : module.default;
  const rasterMode = batch.raster_mode ?? 'stable-cpu';
  if (!['stable-cpu', 'browser'].includes(rasterMode)) throw new Error('raster_mode 只支持 stable-cpu 或 browser');
  const browserArgs = rasterMode === 'stable-cpu'
    ? ['--disable-gpu', '--disable-skia-runtime-opts', '--force-color-profile=srgb']
    : ['--force-color-profile=srgb'];
  const browser = await playwright.chromium.launch({ headless: true, args: browserArgs,
    ...(process.env.ASC_BROWSER_EXECUTABLE ? { executablePath: process.env.ASC_BROWSER_EXECUTABLE } : {}) });
  const report = { renderer: '0.1.0', environment: { node: process.version, platform: os.platform(),
    release: os.release(), arch: os.arch(), browser: browser.version(), browser_args: browserArgs,
    color_profile: 'srgb', raster_mode: rasterMode },
    jobs: [], visual_review: 'not_performed', passed: true };
  try {
    for (const job of batch.jobs) {
      const row = { id: job.id, html: job.html, output: job.output, width: job.width, height: job.height,
        locale: job.locale ?? 'en-US', timezone: job.timezone ?? 'UTC', dpr: job.dpr ?? 1,
        config_sha256: sha(JSON.stringify(job)), passed: false };
      let context;
      try {
        const htmlPath = await local(job.html);
        row.html_sha256 = sha(await fs.readFile(htmlPath));
        context = await browser.newContext({ viewport: { width: job.width, height: job.height },
          deviceScaleFactor: row.dpr, locale: row.locale, timezoneId: row.timezone, reducedMotion: 'reduce',
          colorScheme: job.color_scheme ?? 'light', serviceWorkers: 'block' });
        const blocked = [];
        await context.route('**/*', async route => {
          const url = new URL(route.request().url());
          if (['http:', 'https:'].includes(url.protocol) && !(batch.allowed_origins ?? []).includes(url.origin)) {
            blocked.push(url.origin); await route.abort();
          } else await route.continue();
        });
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        page.setDefaultTimeout(job.timeout_ms ?? 30000);
        await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'load', timeout: job.timeout_ms ?? 30000 });
        if (job.ready_selector) await page.locator(job.ready_selector).waitFor({ state: 'visible' });
        await page.evaluate(async () => {
          await document.fonts.ready;
          await Promise.all([...document.images].map(image => image.decode()));
        });
        await page.addStyleTag({ content: '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}' });
        row.layout = await page.evaluate(({ textSelector, essentialSelector, safe, width, height }) => {
          const rect = e => { const r=e.getBoundingClientRect(); return { x:r.x,y:r.y,width:r.width,height:r.height }; };
          const text = [...document.querySelectorAll(textSelector)].map(e => {
            const style = getComputedStyle(e);
            // 负字距会使末字墨迹超出固有行盒；可见的垂直墨迹不等于被裁切。
            const spacing = Number.parseFloat(style.letterSpacing) || 0;
            const horizontal = e.scrollWidth>e.clientWidth+Math.max(1,-spacing);
            const vertical = e.scrollHeight>e.clientHeight+1;
            const clipsY = style.overflowY !== 'visible';
            return { text:e.textContent, ...rect(e), font:style.fontFamily, size:style.fontSize,
              weight:style.fontWeight, direction:style.direction,
              horizontal_overflow:horizontal, vertical_ink_overflow:vertical,
              vertical_clipping:vertical && clipsY, overflow:horizontal || (vertical && clipsY) };
          });
          const essential = [...document.querySelectorAll(essentialSelector)].map(e => {
            const r=rect(e); const [x,y,w,h]=safe ?? [0,0,width,height];
            return { ...r, outside:r.x<x-1 || r.y<y-1 || r.x+r.width>x+w+1 || r.y+r.height>y+h+1 };
          });
          return { text, essential, font_faces:[...document.fonts].map(f=>({family:f.family,status:f.status})),
            canvas_overflow:document.documentElement.scrollWidth>width+1 || document.documentElement.scrollHeight>height+1 };
        }, { textSelector:job.text_selector ?? '[data-asc-text]',
          essentialSelector:job.essential_selector ?? '[data-asc-essential]', safe:job.safe_rect,
          width:job.width, height:job.height });
        if (blocked.length) throw new Error('页面请求了未允许的远程 origin: ' + [...new Set(blocked)].join(', '));
        if (errors.length) throw new Error('页面脚本错误: ' + errors.join('; '));
        if (row.layout.canvas_overflow || row.layout.text.some(t=>t.overflow) || row.layout.essential.some(t=>t.outside)) {
          throw new Error('测得画布、文字或安全区溢出，详见报告');
        }
        row.measurement_warning = row.layout.text.length ? 'DOM 测量不代替字形及视觉复核' : '没有标记可测文字；需另行检查文字边界';
        row.font_warnings = row.layout.font_faces.filter(f=>f.status==='error');
        for (const required of job.required_font_faces ?? []) {
          if (!row.layout.font_faces.some(f=>f.family.replaceAll('"','')===required && f.status==='loaded')) {
            throw new Error('要求的字体未加载: ' + required);
          }
        }
        const raw = await page.screenshot({ type:'png', animations:'disabled', caret:'hide', omitBackground:false });
        const png = srgbPng(raw);
        const output = await local(job.output, true);
        await fs.mkdir(path.dirname(output), { recursive:true });
        await fs.writeFile(output, png, { flag:'wx' });
        row.sha256 = sha(png); row.passed = true;
      } catch (error) {
        row.error = error.message; report.passed = false;
      } finally {
        if (context) await context.close();
      }
      report.jobs.push(row);
    }
  } finally {
    await browser.close();
    await fs.mkdir(path.dirname(reportPath), { recursive:true });
    await fs.writeFile(reportPath, JSON.stringify(report, null, 2)+'\n', { flag:'wx' });
  }
  process.stdout.write(JSON.stringify({ passed:report.passed, jobs:report.jobs.map(j=>({id:j.id,passed:j.passed,error:j.error})) })+'\n');
  if (!report.passed) process.exitCode=1;
}

main().catch(error => { process.stderr.write('错误: '+error.message+'\n'); process.exitCode=1; });
