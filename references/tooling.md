# 执行工具

方法论与执行器分开。当前附带的工具适合 macOS／Codex 上本地项目状态和 HTML 生产；不包含某款 App 的模拟器 UDID、私有框架、字体文件或个人运行时路径。模拟器、原生采集和 ImageGen 使用当前环境可用的能力，按项目建立适配，不声称已有通用原生采集器。

## 依赖与检查

- `project.py`：Python 3 标准库，无额外依赖。
- `audit_images.py`：Python 3 与 `requirements.txt` 中的 Pillow。
- `render.mjs`：Node.js 与 `package.json` 中锁定的 Playwright，及对应 Chromium 或显式指定的本机浏览器。

依赖未安装时先说明缺口，依据当前环境授权安装到合适位置；不自动改系统配置或在用户项目中启动服务。Playwright 包版本不等于浏览器版本，报告两者。换浏览器／系统／字体后先回放代表样张。

已提供依赖的宿主可通过 `ASC_PLAYWRIGHT_MODULE` 指向可导入的 Playwright 模块文件，通过 `ASC_BROWSER_EXECUTABLE` 指定浏览器。环境变量只存在于使用者机器，不写成仓库固定路径。新安装方式见仓库使用说明。

## 项目状态

```bash
python3 scripts/project.py init /path/to/app-materials --id my-app --name "我的 App"
python3 scripts/project.py status /path/to/app-materials
python3 scripts/project.py validate /path/to/app-materials
python3 scripts/project.py snapshot /path/to/app-materials --id baseline-001 --round round-001
```

init 拒绝覆盖已有状态。snapshot 只接受已记录真实用户确认且无未决问题的轮次，核对所有引用文件哈希；它不替代用户确认，也不表示整套已通过。快照保留状态副本和引用指纹，仍需保留引用文件。旧基准不可覆盖。

## HTML 批量渲染

按项目的已确认构图编写 HTML/CSS，不使用固定主题母版。可编辑文字加 `data-asc-text`，需要安全区检查的元素加 `data-asc-essential`。使用明确背景、字体及语言属性，确认长内容与图片比例。

批次 JSON 放在项目内，所有路径相对项目根目录。例如：

```json
{
  "report": "work/render-round-001.json",
  "allowed_origins": [],
  "jobs": [{
    "id": "hero-zh-phone",
    "html": "sources/hero.zh.html",
    "output": "candidates/round-001/hero.zh.png",
    "width": 1206,
    "height": 2622,
    "locale": "zh-CN",
    "timezone": "Asia/Shanghai",
    "dpr": 1,
    "safe_rect": [48, 48, 1110, 2526]
  }]
}
```

上面的尺寸和区域仅解释数据格式，实际数值来自项目官方规格及设计确认。safe_rect 为 `[x, y, width, height]`，用于 essential 元素，不限制整张背景。

```bash
node scripts/render.mjs /path/to/app-materials render-batch.json
```

工具拒绝输出路径越界、覆盖已有文件或写入 baselines。默认阻止远程资源；需要网络源时在批次明确列出已允许的 origin，更建议下载具有使用依据的资源并固定哈希。图片加载失败、页面错误或测得的文字／安全区溢出会使任务失败，结果报告不等于视觉通过。

负字距的末字墨迹和可见的垂直字形超出行盒单独记录，不直接等同于裁切；横向溢出及垂直被裁切仍拦截。字体加载错误写入 `font_warnings`；任务可设置 `required_font_faces` 数组，要求相应声明字体必须加载，否则失败。固定字形仍应使用可追溯的字体文件；系统 fallback 不能只凭渲染成功就视为已确认一致。

输出为不透明 RGB8 PNG，并写 sRGB 标记；保留渲染像素不重新缩放。渲染器固定 viewport、locale、timezone、DPR，禁用 CSS 动画，并记录色彩与光栅路径；项目仍需固定数据、时间、随机性、动态图片和字体。输出不自动命名为定稿。

批次默认 `raster_mode: "stable-cpu"`，固定 CPU／Skia 基线路径。已有浏览器生产源可以明确使用 `raster_mode: "browser"` 保留浏览器默认光栅路径。二者可能改变图像缩放和抗锯齿，必须先确认该项目的样张再冻结；不要为追求零差异，把历史项目未经确认迁到另一条路径。原路径若仅有微小色阶噪声，也要如实记录，容差由项目标准决定。

浏览器参数参考 Chromium 的 [GPU 参数定义](https://chromium.googlesource.com/chromium/src/+/master/content/test/gpu/gpu_tests/common_browser_args.py) 和 [公共参数定义](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/content/public/common/content_switches.cc)。参数属于执行环境的一部分，不能据此保证跨系统逐像素一致，仍需实际重复生产核对。

## 图片审计

```json
{
  "images": [{"path": "candidates/round-001/hero.zh.png", "width": 1206, "height": 2622, "rgb8": true, "srgb": true, "opaque": true}],
  "comparisons": [{
    "left": "candidates/round-001/hero.zh.png",
    "right": "candidates/repeat/hero.zh.png",
    "regions": [[0, 0, 1206, 2622]],
    "max_channel_delta": 0,
    "max_changed_fraction": 0,
    "reason": "相同输入与环境重复生产"
  }]
}
```

```bash
python3 scripts/audit_images.py /path/to/app-materials audit-batch.json --report work/audit-round-001.json
```

审计只读取图片，写指定 JSON 报告。比较区域必须明确，阈值需要理由；不预设不同语言整图相同。尺寸、色彩和区域差异检查不代替内容正确、真实功能与视觉验收。原生采集的完成清单、切片重叠、真实输入输出等按项目适配器另外检查。
