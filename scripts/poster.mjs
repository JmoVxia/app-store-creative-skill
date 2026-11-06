#!/usr/bin/env node
// 准备海报项目与批次；实际渲染、图片审计复用现有执行器。
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const here = path.dirname(fileURLToPath(import.meta.url));
const exists = async p => { try { await fs.access(p); return true; } catch { return false; } };
const hash = b => createHash('sha256').update(b).digest('hex');
const validId = s => typeof s === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.-]*$/.test(s) && !['.', '..'].includes(s);
const positive = (n, name) => { if (!Number.isFinite(n) || n <= 0) throw Error(name + '需要正数'); return n; };
const nonnegative = (n, name) => { if (!Number.isFinite(n) || n < 0) throw Error(name + '需要非负数'); return n; };
const text = (s, name) => { if (typeof s !== 'string' || !s.trim()) throw Error(name + '缺失'); return s; };

async function local(root, name) {
  if (typeof name !== 'string' || !name || path.isAbsolute(name)) throw Error('需要项目相对路径: ' + name);
  const p = path.resolve(root, name), rel = path.relative(root, p);
  if (!rel || rel === '..' || rel.startsWith('..' + path.sep)) throw Error('路径超出项目: ' + name);
  let parent = p;
  while (!(await exists(parent))) parent = path.dirname(parent);
  const real = await fs.realpath(parent);
  if (real !== root && !real.startsWith(root + path.sep)) throw Error('符号链接超出项目: ' + name);
  return p;
}

async function init(project) {
  await fs.mkdir(path.resolve(project), { recursive: true });
  const root = await fs.realpath(path.resolve(project));
  const names = ['poster.json', 'poster/master.html'];
  for (const name of names) if (await exists(await local(root, name))) throw Error('拒绝覆盖: ' + name);
  await fs.mkdir(path.join(root, 'poster'), { recursive: true });
  await fs.copyFile(path.join(here, '../assets/poster/master.html'), path.join(root, 'poster/master.html'), fs.constants.COPYFILE_EXCL);
  await fs.copyFile(path.join(here, '../assets/poster/poster.json'), path.join(root, 'poster.json'), fs.constants.COPYFILE_EXCL);
  console.log(JSON.stringify({ project: root, configured: false, next: '填写poster.json中的文案与图片相对路径；空素材不能出图。' }));
}

async function prepare(project, configName, id) {
  if (!validId(id)) throw Error('--id需要新的轮次标识');
  const root = await fs.realpath(path.resolve(project));
  const configPath = await local(root, configName), configBytes = await fs.readFile(configPath);
  const config = JSON.parse(configBytes), templatePath = await local(root, config.template);
  if (config.version !== 1) throw Error('仅支持poster配置version: 1');
  const master = await fs.readFile(templatePath, 'utf8');
  if (master.split('/*POSTER_SPEC*/ null').length !== 2) throw Error('母版必须含一个POSTER_SPEC标记');
  const workName = 'work/' + id, outputName = 'candidates/' + id;
  for (const name of [workName, outputName]) if (await exists(await local(root, name))) throw Error('轮次已存在，拒绝覆盖: ' + name);
  const resources = new Map([[configName, hash(configBytes)], [config.template, hash(master)]]);
  const t = config.tokens;
  if (!t || typeof t !== 'object') throw Error('缺少tokens');
  for (const key of ['badgeSize', 'badgeFont', 'arrowShaft', 'arrowHeadWidth', 'arrowHeadHeight', 'titleFont', 'subtitleFont', 'stepTitleHeight', 'stepTitleFont']) positive(t[key], 'tokens.' + key);
  for (const key of ['paperPadding', 'paperRadius', 'badgeRadius', 'badgeGap', 'arrowInset', 'stepTitleGap']) nonnegative(t[key], 'tokens.' + key);
  for (const key of ['background', 'ink', 'muted', 'accent', 'paperBorder', 'paperShadow', 'fontFamily']) text(t[key], 'tokens.' + key);
  const devices = Object.entries(config.devices ?? {}), locales = Object.entries(config.locales ?? {});
  if (!devices.length || !locales.length) throw Error('需要devices和locales');
  const materialRecords = [], prepared = [], outputs = [];
  async function image(name, target, role) {
    if (typeof name !== 'string' || !name) throw Error('缺少素材: ' + role);
    const p = await local(root, name), b = await fs.readFile(p).catch(() => { throw Error('素材不存在: ' + role + ' / ' + name); });
    if (b.length < 33 || b.subarray(0, 8).toString('hex') !== '89504e470d0a1a0a') throw Error('starter素材需要PNG: ' + name);
    const dimensions = [b.readUInt32BE(16), b.readUInt32BE(20)];
    if (dimensions.some(n => n <= 0)) throw Error('PNG尺寸无效: ' + name);
    if (target && Math.abs((target[0] / target[1]) / (dimensions[0] / dimensions[1]) - 1) > 1e-6) throw Error('素材比例不符，请先按槽位制作，禁止拉伸: ' + role + ' / ' + name + '，需要比例' + target.join(':') + '，实际' + dimensions.join(':'));
    resources.set(name, hash(b));
    const record = { path: name, sha256: hash(b), dimensions, role };
    materialRecords.push(record); return record;
  }
  for (const [locale, l] of locales) {
    if (!validId(locale)) throw Error('无效locale标识');
    text(l.browserLocale, locale + '.browserLocale');
    if (l.fontFamily !== undefined) text(l.fontFamily, locale + '.fontFamily');
    const pages = Object.entries(l.pages ?? {});
    if (!pages.length) throw Error('本地化没有pages: ' + locale);
    for (const [device, d] of devices) {
      if (!validId(device)) throw Error('无效设备标识');
      if (!Array.isArray(d.canvas) || d.canvas.length !== 2 || d.canvas.some(n => !Number.isInteger(n) || n <= 0)) throw Error('canvas需要两个正整数');
      for (const key of ['headerHeight', 'labelHeight', 'bodyTop', 'cardWidth', 'columnGap', 'groupHeight', 'labelFont']) positive(d[key], device + '.' + key);
      for (const key of ['labelY', 'inputGap', 'stepGap']) nonnegative(d[key], device + '.' + key);
      const [width, height] = d.canvas, pad = t.paperPadding, cw = d.cardWidth - 2 * pad;
      const gw = 2 * d.cardWidth + d.columnGap, gx = (width - gw) / 2, rx = gx + d.cardWidth + d.columnGap;
      if (d.stepTitleFont !== undefined) positive(d.stepTitleFont, device + '.stepTitleFont');
      if (cw <= t.badgeSize + t.badgeGap || gx < 0 || d.bodyTop + d.groupHeight > height || d.labelY + d.labelHeight > d.bodyTop || d.headerHeight > d.labelY || t.arrowHeadWidth + 2 * t.arrowInset >= d.columnGap || t.arrowShaft > t.arrowHeadHeight || t.arrowHeadHeight > d.groupHeight) throw Error('设备网格越界或间距冲突: ' + device);
      for (const [page, p] of pages) {
        if (!validId(page)) throw Error('无效页码');
        if (!['conversion', 'steps'].includes(p.layout)) throw Error('layout只支持conversion/steps');
        if (!Array.isArray(p.labels) || p.labels.length !== 2) throw Error('每页需要两个列名');
        p.labels.forEach((s, i) => text(s, page + '.labels[' + i + ']'));
        const data = p.devices?.[device];
        if (!data) throw Error('缺少页面设备素材: ' + locale + '/' + device + '/' + page);
        const htmlName = workName + '/' + locale + '-' + device + '-' + page + '.html';
        const output = outputName + '/' + locale + '/' + device + '/' + page + '.png';
        if (outputs.includes(output)) throw Error('组合重复: ' + output); outputs.push(output);
        const components = [], cards = [];
        function component(name, rect, extra = {}) { components.push({ id: name, selector: '[data-component="' + name + '"]', rect, tolerance_px: 0.03, ...extra }); }
        function assetUrl(record) { return path.relative(path.dirname(path.join(root, htmlName)), path.join(root, record.path)).split(path.sep).map(encodeURIComponent).join('/'); }
        function addCard(name, rect, record, imgRect, badge, stepTitle) {
          component(name, rect); component(name + '-image', imgRect, { image_fit: 'equal-ratio' });
          if (badge !== undefined) component(name + '-badge', [rect[0] + pad, rect[1] + pad, t.badgeSize, t.badgeSize]);
          cards.push({ name, rect, image: assetUrl(record), imgRect, badge, stepTitle });
        }
        const result = await image(data.result, [cw, d.groupHeight - 2 * pad], locale + '/' + device + '/' + page + ':result');
        addCard('result', [rx, d.bodyTop, d.cardWidth, d.groupHeight], result, [rx + pad, d.bodyTop + pad, cw, d.groupHeight - 2 * pad]);
        if (p.layout === 'conversion') {
          if (!Array.isArray(data.inputs) || data.inputs.length < 2) throw Error('conversion需要至少两个inputs');
          const count = data.inputs.length, ch = (d.groupHeight - (count - 1) * d.inputGap) / count, ih = ch - 2 * pad;
          positive(ih, 'input高度');
          if (ih < t.badgeSize) throw Error('input视窗不能容纳完整角标');
          const numbers = new Set();
          for (let i = 0; i < count; i++) {
            const input = data.inputs[i];
            if (!Number.isInteger(input.number) || input.number <= 0 || numbers.has(input.number)) throw Error('input序号需要唯一正整数'); numbers.add(input.number);
            const rec = await image(input.asset, [cw, ih], locale + '/' + device + '/' + page + ':input-' + i);
            const y = d.bodyTop + i * (ch + d.inputGap);
            addCard('input-' + i, [gx, y, d.cardWidth, ch], rec, [gx + pad, y + pad, cw, ih], input.number);
          }
        } else {
          if (!Array.isArray(data.steps) || data.steps.length !== 3) throw Error('steps布局需要三个steps');
          const records = [];
          for (let i = 0; i < 3; i++) { text(data.steps[i].title, '步骤短标题'); records.push(await image(data.steps[i].asset, null, locale + '/' + device + '/' + page + ':step-' + i)); }
          const heights = records.map(r => cw * r.dimensions[1] / r.dimensions[0]);
          const base = 2 * pad + t.stepTitleHeight + t.stepTitleGap;
          const extra = (d.groupHeight - 2 * d.stepGap - heights.reduce((a, b) => a + b, 0) - 3 * base) / 3;
          nonnegative(extra, '步骤图超出槽位；extra');
          if (t.badgeSize > t.stepTitleHeight) throw Error('stepTitleHeight小于角标');
          let y = d.bodyTop;
          for (let i = 0; i < 3; i++) {
            const ch = heights[i] + base + extra;
            addCard('step-' + i, [gx, y, d.cardWidth, ch], records[i], [gx + pad, y + pad + t.stepTitleHeight + t.stepTitleGap + extra / 2, cw, heights[i]], i + 1, data.steps[i].title);
            component('step-' + i + '-title', [gx + pad + t.badgeSize + t.badgeGap, y + pad, cw - t.badgeSize - t.badgeGap, t.stepTitleHeight]);
            y += ch + d.stepGap;
          }
        }
        const labelRects = [[gx, d.labelY, d.cardWidth, d.labelHeight], [rx, d.labelY, d.cardWidth, d.labelHeight]];
        labelRects.forEach((r, i) => component('label-' + i, r));
        const arrowRect = [gx + d.cardWidth + t.arrowInset, d.bodyTop + d.groupHeight / 2 - t.arrowHeadHeight / 2, d.columnGap - 2 * t.arrowInset, t.arrowHeadHeight];
        component('arrow', arrowRect);
        let header;
        if (data.headerImage) {
          const r = await image(data.headerImage, [width, d.headerHeight], locale + '/' + device + '/' + page + ':header');
          header = { image: assetUrl(r) }; component('header', [0, 0, width, d.headerHeight], { image_fit: 'equal-ratio' });
        } else {
          if (!Array.isArray(p.title) || !p.title.length) throw Error('需要title行数组或headerImage');
          p.title.forEach(s => text(s, 'title')); text(p.subtitle, 'subtitle');
          const titleY = nonnegative(d.titleY ?? 110, 'titleY'), subtitleY = nonnegative(d.subtitleY ?? 420, 'subtitleY');
          const titleRect = [48, titleY, width - 96, t.titleFont * 1.14 * p.title.length];
          const subtitleRect = [48, subtitleY, width - 96, t.subtitleFont * 1.2];
          if (titleRect[1] + titleRect[3] > subtitleY || subtitleRect[1] + subtitleRect[3] > d.headerHeight) throw Error('顶部文字重叠或超过headerHeight: ' + locale + '/' + device + '/' + page);
          header = { title: p.title, subtitle: p.subtitle, titleRect, subtitleRect };
          component('title', titleRect); component('subtitle', subtitleRect);
        }
        const spec = { locale, canvas: d.canvas, tokens: { ...t, fontFamily: l.fontFamily ?? t.fontFamily }, device: d, header, labels: p.labels, labelRects, arrowRect, cards };
        const html = master.replace('/*POSTER_SPEC*/ null', JSON.stringify(spec).replace(/</g, '\\u003c'));
        resources.set(htmlName, hash(html));
        prepared.push({ htmlName, html, job: { id: locale + '-' + device + '-' + page, html: htmlName, output, width, height, dpr: 1, locale: l.browserLocale, timezone: 'UTC', ready_selector: '#poster-ready', components } });
      }
    }
  }
  const frozen = [...resources].map(([name, sha256]) => ({ path: name, sha256 }));
  const render = { report: workName + '/render-report.json', raster_mode: config.rasterMode ?? 'stable-cpu', expected_outputs: outputs, resources: frozen, jobs: prepared.map(p => p.job) };
  const audit = { resources: frozen, images: prepared.map(({ job: j }) => ({ path: j.output, width: j.width, height: j.height, rgb8: true, srgb: true, opaque: true })), coverage: { expected_paths: outputs, directory: outputName, glob: '**/*.png', reject_identical: false } };
  await fs.mkdir(await local(root, workName), { recursive: true });
  for (const p of prepared) await fs.writeFile(await local(root, p.htmlName), p.html, { flag: 'wx' });
  for (const [name, obj] of [['render-batch.json', render], ['audit-batch.json', audit], ['material-manifest.json', { scope: '仅生产与几何契约；视觉、来源和用户确认另记', materials: materialRecords }]]) await fs.writeFile(await local(root, workName + '/' + name), JSON.stringify(obj, null, 2) + '\n', { flag: 'wx' });
  console.log(JSON.stringify({ jobs: prepared.length, render_batch: workName + '/render-batch.json', audit_batch: workName + '/audit-batch.json', output_directory: outputName }));
}

try {
  const [command, project, configName, ...options] = process.argv.slice(2);
  if (command === 'init' && project && !configName) await init(project);
  else if (command === 'prepare' && project && configName && options.length === 2 && options[0] === '--id') await prepare(project, configName, options[1]);
  else throw Error('用法: node scripts/poster.mjs init <项目根> | prepare <项目根> <配置相对路径> --id <新轮次>');
} catch (error) { console.error(error.message); process.exitCode = 1; }
