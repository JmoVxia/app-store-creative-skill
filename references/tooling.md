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

## 海报起稿

转换型、步骤型海报可用`poster.mjs init/prepare`从一份参数生成可编辑网页和既有执行器的批次；命令、素材槽与失败修复路径见[海报生产](poster-production.md)。它不生成真实App界面，不自动填入虚假素材，也不替代首样审美判断。

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

工具拒绝输出路径越界、覆盖已有文件或写入 baselines。默认阻止远程资源；需要网络源时在批次明确列出已允许的 origin，更建议下载具有使用依据的资源并固定哈希。HTML 图像解码失败、CSS mask／背景／字体等请求失败、HTTP 错误、页面错误或测得的文字／安全区溢出会使任务失败，结果报告不等于视觉通过。

本执行器从 `file://` 打开本地 HTML，在受控 headless 实例使用 `--allow-file-access-from-files`，以支持本地 CSS 遮罩等资源，并把参数写入环境报告。其他渲染环境要实测这条路径：仅文件存在、`img.decode()` 成功或 DOM 尺寸正确，不证明 CSS 遮罩已正常合成。需要改为内嵌 data URI 时，从同一冻结原件派生并记录哈希，不能以换来源掩盖空屏。最终还要用屏内原件映射检查防止“整个屏幕透明也没有外溢”的假通过。

负字距的末字墨迹和可见的垂直字形超出行盒单独记录，不直接等同于裁切；横向溢出及垂直被裁切仍拦截。字体加载错误写入 `font_warnings`；任务可设置 `required_font_faces` 数组，要求相应声明字体必须加载，否则失败。固定字形仍应使用可追溯的字体文件；系统 fallback 不能只凭渲染成功就视为已确认一致。

输出为不透明 RGB8 PNG，并写 sRGB 标记；保留渲染像素不重新缩放。渲染器固定 viewport、locale、timezone、DPR，禁用 CSS 动画，并记录色彩与光栅路径；项目仍需固定数据、时间、随机性、动态图片和字体。输出不自动命名为定稿。

批次默认 `raster_mode: "stable-cpu"`，固定 CPU／Skia 基线路径。已有浏览器生产源可以明确使用 `raster_mode: "browser"` 保留浏览器默认光栅路径。二者可能改变图像缩放和抗锯齿，必须先确认该项目的样张再冻结；不要为追求零差异，把历史项目未经确认迁到另一条路径。原路径若仅有微小色阶噪声，也要如实记录，容差由项目标准决定。

浏览器参数参考 Chromium 的 [GPU 参数定义](https://chromium.googlesource.com/chromium/src/+/master/content/test/gpu/gpu_tests/common_browser_args.py) 和 [公共参数定义](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/content/public/common/content_switches.cc)。参数属于执行环境的一部分，不能据此保证跨系统逐像素一致，仍需实际重复生产核对。

### 整套与组件契约

需要统一设备框、卡片或其他固定组件时，从项目的[整套规范](series-consistency.md)生成以下可选字段，不要另抄一组独立数值：

- 批次 `expected_outputs`：完整预期输出相对路径数组，须与 `jobs[].output` 一一相等，缺失、多余、重复在出图前拒绝。它不能证明外部脚本未绕过母版，仍需成品目录覆盖核验。
- 批次 `resources`：`[{"path":"materials/frame.png","sha256":"对应文件的64位SHA256"}]`。对框、遮罩、字体、状态栏及其他冻结依赖逐项记录，在任何 PNG 写入前核验，报告保存实际哈希；不能用 mtime 作为命中依据。
- 任务 `components`：要检查的组件数组。每个组件的 `id`、`selector` 唯一，选择器须恰好命中一个元素；DOM 矩形、指定 computed 样式及图片比例均写入报告。失败时不写该页 PNG。

组件字段示意（数值只说明格式，须替换为项目规范）：

```json
{
  "id": "screen-content",
  "selector": "canvas[data-asc-screen]",
  "rect": [72, 220, 320, 640],
  "tolerance_px": 0.02,
  "styles": {"padding": "0px", "maskMode": "luminance"},
  "image_fit": "equal-ratio",
  "ratio_tolerance": 0.0001
}
```

`rect` 为最终视口 CSS 像素中的 `[x,y,width,height]`，`tolerance_px` 为各项最大误差，缺省为 `0.02px`。`styles` 对指定 computed 值作精确比较，需按浏览器实际序列化写值；不是只读 HTML 内联样式。`image_fit: "equal-ratio"` 仅用于 `img` 或 `canvas`，比较原生像素与扣除 CSS padding、border 后的内容盒比例；`ratio_tolerance` 缺省为 `1e-6`，度量为 `abs(内容盒比例 / 原件比例 − 1)`，不能与像素误差混用，分数尺寸需显式选用能解释布局舍入的值。工具不自动放宽；`object-fit:none` 的裁切和 `scale-down` 留白也会拒绝。旋转或非等比变换不适用于这项简单几何验证，应改查未变换源或另设项目验证。灰度屏幕遮罩可显式检查 `maskMode: "luminance"`，但该 DOM 检查仍不替代最终 PNG 四角／四边核验。

组件本身不渲染设备框，也不推断哪些原生控件可以裁切。没有设备框的素材可仅约束实际共享卡片、标题等组件；旧批次不填这些字段时继续按原行为工作。

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

### 非矩形固定区与外溢

`comparisons` 的每项可增加 `mask` 与 `mask_mode`。掩码必须是与成品同尺寸的项目相对 PNG；`mask_mode` 必须显式为 `alpha` 或 `luminance`，不能根据扩展名猜测。`alpha` 要求原图实际有 alpha／透明信息；`luminance` 使用亮度并结合原 alpha。有效值大于 0 的像素与各个 `regions` 取交集作非加权比较，每区记录 `checked_pixels`；任一区为空即失败。工具不自动缩放、内缩或扩张掩码，抗锯齿带由项目预先确定并冻结。

机身／圆角卡片外侧是纯色时，可用 `background_checks` 检查最终图上的越界像素：

```json
{
  "background_checks": [{
    "path": "candidates/round-001/hero.zh.png",
    "mask": "materials/masks/outside-device.png",
    "mask_mode": "luminance",
    "regions": [[0, 0, 1206, 2622]],
    "color": [255, 255, 255],
    "max_channel_delta": 0,
    "max_changed_fraction": 0,
    "reason": "声明的机身外部必须与本页白色背景一致"
  }]
}
```

实际项目把四角和四边列为各自的显式区域，避免只检查了某一侧。复杂背景改用 `comparisons` 对独立背景图比较。阈值、选区和原因必须给出；不要为让结果通过而扩大排除区域。工具只比较你声明的选区，不能证明掩码本身正确或全边界已被覆盖。

### 矩阵、重复图与依赖

审计批次也支持 `resources: [{path,sha256}]`，用于从发布检查再次核对实际冻结依赖。`coverage` 可单独运行：

```json
{
  "coverage": {
    "expected_paths": ["candidates/round-001/hero.zh.png"],
    "directory": "candidates/round-001",
    "glob": "**/*.png",
    "reject_identical": false
  }
}
```

预期清单从目标矩阵生成，工具与实际目录扫描集合核对，拒绝缺失、多余及重复路径。批次若包含 `images` 键，其条目集合也必须匹配（显式 `images: []` 不等于省略）。省略 `images` 时可以仅检查覆盖和重复，不能据此声称已按指定 RGB8、颜色与尺寸约束验收。

相同文件哈希和相同解码像素分别分组报告；共用同一截图可有合理依据，因此仅在 `reject_identical: true` 时拒绝相同图。预期重复也应在项目记录用途，不能用关闭重复门禁掩盖错语言或旧成品旁路。所有报告仍不表示已做视觉自审或用户确认。
