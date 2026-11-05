# App Store Creative Skill

[English](README.en.md) · [MIT](LICENSE)

为每个 App 建立自己的商店素材标准，再稳定执行。一个主入口，内部模块化；支持新项目、已有成果接入、局部修改和换会话续做。有源码、无源码都可以使用。

这是一套方法技能，不预设风格、张数、顺序或某款 App 的固定模板。设计探索保留创造性；确认后固定参数、素材与生产环境，支持再次出图。

## 使用过程

从产品想解决的问题开始，为每页选一个有说服力的场景，再决定文案、配色和构图。普通截图在分镜阶段就按设备与本地化安排足够的真实操作画面，把功能和结果放在读者看得清的位置。

先建立整套规范，再搭可复用网页母版，从槽位反推素材；用目标设备和语言的真实 App 界面出第一张最终尺寸 PNG。首样已按交付标准检查四角四边、比例、间距与完整控件，确认后扩到整套，逐组复算实际使用页，逐张检查语言、取景及像素细节。已有定稿和审核反馈从对应步骤继续。[设计与分镜](references/design-rounds.md) · [整套一致性](references/series-consistency.md) · [素材与生产](references/material-production.md) · [分层验收](references/quality.md)

- 普通截图、Header、Search Results 共享风格，按各自用途独立构图。
- 素材可来自用户、真实 App／模拟器、脚本、ImageGen 和互联网；来源与用途可追溯，不伪造功能结果。
- 全部语言和设备前置考虑；确认母版与高风险样张后批量生产，超出规则再确认。
- 字体、文案、布局、素材和环境一起固定。同提示词重新生成 AI 图片不保证相同，确认的主视觉直接复用。
- 机身、屏幕视口、原生工作区与内容卡片的留白分别定义；手机与平板各自锁定比例和状态栏。需要拟真 Apple 机身时核对官方设备框使用规则，冻结同一原件；内容不得冒出框，不能靠拉伸或裁掉控件抹平真实差异。
- 全矩阵使用相同参数来源与验收入口；复制旧图和 mtime 都不算检查。固定层、角边外溢、空掩码、资源变化、遗漏页和意外重复在交付前检查，明确机器与视觉核验的覆盖范围。
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
为我的新 App 创作商店截图。按卖点和真实使用场景编排分镜，确定网页母版，再给我看一张用真实素材完成的 PNG。
```

继续已有项目时提供生产目录，并说明本轮目标。例如“只新增日语”“替换第二页素材”或“恢复未完成的设计确认”。沟通语言、App 界面语言与商店素材语言分别设置。

## 方法与执行能力

阅读和对齐方法不需要安装渲染依赖。实际生产前检查工具，按授权选择路径：

| 能力 | 当前提供 |
| --- | --- |
| 方法与模块 | `SKILL.md` 和按需读取的 `references/` |
| 项目状态、指纹、基准 | Python 标准库脚本 `scripts/project.py` |
| 本地 HTML 批量渲染、矩阵和组件几何／样式／比例约束 | Node.js／Playwright 脚本 `scripts/render.mjs` |
| 图片规格、掩码区域／背景外溢、目录覆盖及资源哈希 | Pillow 脚本 `scripts/audit_images.py` |
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

首版执行器的历史验证范围保存在 [validation/status.json](validation/status.json)。首版重点在 macOS／Codex 环境验证原项目回放、图片检查和同参数重复生产。跨 App 项目待提供，明确标为待验证；其他平台及各 App 的原生采集器也不能据此宣称已验证。

当前实证：54 张既有定稿格式检查通过；固定 CPU 路径下六组横图重复渲染，整图 0 像素差异。历史浏览器路径与原定稿回放存在最多 1 色阶差异，严格零差异未通过；新路径不能未经确认替换旧项目。统计见 [验证结果](validation/results.json)，不包含原项目素材。

0.3.0 增加整套一致性规范和可选工具契约：33 项图片审计用例、26 次隔离 HTML 验证符合预期；用增强后的通用脚本对既有 48 张最终 PNG 完成 90 项掩码比较、384 项四角四边检查。独立双设备／双语言自编排版演练完成 4 组出图与重复字节一致性核验，并据此修复本地 CSS 遮罩空屏误通过。该演练不是独立真实 App 或商店提交实证；不公开项目原件和私人路径。

脚本通过不代表视觉或用户确认。静态检查、网页渲染、真实 App 采集、引擎运行、编译／测试和商店提交分别记录。最终素材仍需按目标位置的当次 Apple 官方规格核对。

## 维护与许可

核心方法中文维护，本说明提供中英入口，交互使用用户的语言。项目固定所用技能、模板、字体、素材与环境版本；新版本不会自动迁移旧项目。修改参数或素材时，先检查依赖和受影响确认，见 [维护与迁移](references/lifecycle.md)。

代码与原创方法文档采用 MIT。第三方字体、图片及项目素材按各自许可处理；使用本技能不要求公开使用者的 App 源码、品牌素材或生产资料。不要在 Issue、PR 或公开示例中提交凭证和私有数据。
