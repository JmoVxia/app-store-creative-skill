# App Store Creative Skill

[English](README.en.md) · [MIT](LICENSE)

为每个 App 建立自己的商店素材标准，再稳定执行。一个主入口，内部模块化；支持新项目、已有成果接入、局部修改和换会话续做。有源码、无源码都可以使用。

这是一套方法技能，不预设风格、张数、顺序或某款 App 的固定模板。设计探索保留创造性；确认后固定参数、素材与生产环境，支持再次出图。

## 使用过程

用户先描述 → 补问并确认理解 → 核对代码／资料／素材 → 研究同类与跨品类参考 → 准备全语言文案和设备约束 → 整体方向示意 → 素材样张与关联细化 → 应用回整体复核 → 确认后批量生产 → 逐张自审与用户确认。

按依赖选择模块，不强制每次重走全流程。每轮只有一组相关目标，以问答、选择或示意校准，保存确认与否决原因，再进入下一轮。已确认基准与候选修改分开，局部整改只重新打开受影响内容。

- 普通截图、Header、Search Results 共享风格，按各自用途独立构图。
- 素材可来自用户、真实 App／模拟器、脚本、ImageGen 和互联网；来源与用途可追溯，不伪造功能结果。
- 全部语言和设备前置考虑；确认母版与高风险样张后批量生产，超出规则再确认。
- 字体、文案、布局、素材和环境一起固定。同提示词重新生成 AI 图片不保证相同，确认的主视觉直接复用。
- 官方规格启动时核对并保存快照，交付前复核变化；旧项目不自动升级。

## 安装到 Codex

将整个仓库作为一个技能安装，目标目录不存在时执行：

```bash
git clone --depth 1 https://github.com/JmoVxia/app-store-creative-skill.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/app-store-creative-skill"
```

也可使用环境提供的 skill-installer 安装该仓库根目录。若目录已存在，先确认版本和本地改动，不要直接覆盖。安装后在下一轮对话中使用：

```text
使用 $app-store-creative-skill。
我想为这款 App 制作商店素材，先听我描述，再逐轮追问和确认。
```

继续已有项目时提供生产目录，并说明本轮目标。例如“只新增日语”“替换第二页素材”或“恢复未完成的设计确认”。沟通语言、App 界面语言与商店素材语言分别设置。

## 方法与执行能力

阅读和对齐方法不需要安装渲染依赖。实际生产前检查工具，按授权选择路径：

| 能力 | 当前提供 |
| --- | --- |
| 方法与模块 | `SKILL.md` 和按需读取的 `references/` |
| 项目状态、指纹、基准 | Python 标准库脚本 `scripts/project.py` |
| 本地 HTML 批量渲染与边界测量 | Node.js／Playwright 脚本 `scripts/render.mjs` |
| 图片规格及显式区域比较 | Pillow 脚本 `scripts/audit_images.py` |
| 原生采集、引擎结果、ImageGen | 根据使用者的 App 和当前可用工具接入；没有固定私有适配器 |

需要附带的渲染工具时，在技能目录执行：

```bash
npm ci --ignore-scripts
npx playwright install chromium
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

建议 Node.js 20+、Python 3.10+。默认使用 Playwright 对应的 Chromium；已有运行时可通过 `ASC_PLAYWRIGHT_MODULE` 和 `ASC_BROWSER_EXECUTABLE` 指定，不能把使用者路径写入公开配置。工具变化后先做代表图回放。

初始化独立的 App 生产目录：

```bash
python3 scripts/project.py init /path/to/app-materials --id my-app --name "我的 App"
python3 scripts/project.py status /path/to/app-materials
```

每个 App 的规范、确认、素材、真实采集和输出都保存在自己的项目目录，**不提交到本技能仓库**。项目结构、参数契约和批次格式见 [项目契约](references/project-contract.md) 与 [工具说明](references/tooling.md)。脚本不提供自动批准或不可恢复清理功能。

## 验证范围

具体状态与限制保存在 [validation/status.json](validation/status.json)。首版重点在 macOS／Codex 环境验证原项目回放、图片检查和同参数重复生产。跨 App 项目待提供，明确标为待验证；其他平台及各 App 的原生采集器也不能据此宣称已验证。

当前实证：54 张既有定稿格式检查通过；固定 CPU 路径下六组横图重复渲染，整图 0 像素差异。历史浏览器路径与原定稿回放存在最多 1 色阶差异，严格零差异未通过；新路径不能未经确认替换旧项目。统计见 [验证结果](validation/results.json)，不包含原项目素材。

脚本通过不代表视觉或用户确认。静态检查、网页渲染、真实 App 采集、引擎运行、编译／测试和商店提交分别记录。最终素材仍需按目标位置的当次 Apple 官方规格核对。

## 维护与许可

核心方法中文维护，本说明提供中英入口，交互使用用户的语言。项目固定所用技能、模板、字体、素材与环境版本；新版本不会自动迁移旧项目。修改参数或素材时，先检查依赖和受影响确认，见 [维护与迁移](references/lifecycle.md)。

代码与原创方法文档采用 MIT。第三方字体、图片及项目素材按各自许可处理；使用本技能不要求公开使用者的 App 源码、品牌素材或生产资料。不要在 Issue、PR 或公开示例中提交凭证和私有数据。
