# 项目契约

## 项目与技能分开

技能仓库只保存通用方法和工具。每个 App 的生产目录位于自己的工作区，不放在技能目录内；素材、采集原件、凭证和个人路径不进入公开仓库。下面的目录是状态交换契约，不是固定视觉模板：

```text
project.json                 当前工作状态、参数组、环境与规格快照
assets.json                  素材来源、哈希、用途及派生关系
rounds/                      每轮目标、示意、反馈、确认与依赖
baselines/<id>/              已确认状态快照及引用文件哈希
sources/                     可编辑文案、数据、HTML/CSS、项目脚本
materials/                   输入素材、原生采集、真实导出、冻结艺术素材
candidates/                  当前待确认的示意及成图
deliverables/                本次确认的正式输出
archive/                     停用稿及历史版本，不参与当前生产
work/                        可再生缓存、运行日志、临时结果
```

只有实际需要时才创建后面的目录。路径使用相对项目根目录的位置。外部来源导入项目后记录原来源；不要在可移植配置中写个人绝对路径或嵌入凭证。

## project.json

初始结构由 `scripts/project.py init` 生成。未知值为空，不能当作已确认。关键字段：

| 字段 | 内容 |
| --- | --- |
| schema_version / skill_version | 数据契约和项目采用的技能版本 |
| project | ID、名称、简述、源码／资料入口与已知事实 |
| languages | communication、app_ui、store 三种语言设置 |
| targets | 平台、设备、方向、商店位置、地区与目标语言组合 |
| phase / next_action / open_questions | 当前模块、下一步及未决问题 |
| parameters | 按作用域组织的关联参数组 |
| scenes | 各页意图、证据、视觉任务、内容约束与槽位 |
| environment | 工具、版本、字体哈希、设备、系统、locale、DPR 等 |
| specifications | 官方 URL、检查日期、适用位置、字段快照和差异 |
| capabilities | 可用工具、已检查能力、缺口；不是执行授权 |
| active_baseline | 当前确认基准 ID，尚无确认时为 null |
| validation | 实际完成／待验证／失败及证据，不用布尔值掩盖范围 |

参数组建议结构：`value`、`unit`、`scope`、`source`、`fixed`、`allowed_range`、`adaptation_order`、`depends_on`、`confirmed_by`、`check`。`value` 可以是相关参数对象，不要求所有值都是数字。区分共享值、位置／设备／语言变体和明确例外。

## 轮次文件 rounds/<id>.json

最小字段为 `id`、`module`、`objective`、`status`、`depends_on`、`inputs`、`outputs`、`parameter_groups`、`decisions`、`rejections`、`open_questions`、`review`、`confirmation`、`budget`。

- 状态：draft → review → confirmed 或 rejected。已确认／否决的轮次作为历史证据保留；新的修改使用新轮次。
- `depends_on` 引用其他轮次 ID；仅包含本轮真正依赖的结果。
- `inputs`、`outputs` 和 `review.artifacts` 的元素为 `{ "path": "项目相对路径", "sha256": "文件SHA256" }`。确认后文件变化即失去同版证据，不能只沿用文件名。
- `review` 保存本轮问题、选项／示例、推荐及实际反馈。各类轮次按需要采用示意，不要求非视觉问题也造图。
- `confirmation` 只在用户实际确认后填写：`source: "user"`、原始确认 `message`、`at`、`scope`。不能由脚本生成用户授权或由助手建议代替。
- `parameter_groups` 指明这次究竟确认哪些参数组。不能因为用户选了一个风格方向，就把未展示的排版细节也标为确认。
- `asset_ids` 列出本轮涉及的索引素材，作为确认后冻结其输入派生链的依据；源码或模板的外部依赖也须纳入，工具不能自动解析所有 HTML/CSS/脚本引用。
- `parameter_sha256` 记录该组展示给用户时的值指纹，可用 `project.py fingerprint --parameter <组名>` 计算；指纹不包含 `confirmed_by` 状态指针。改值后不能继续挂旧轮次的确认。
- `budget` 记录本轮候选量、生成／采集预算、停止条件、实际消耗及需要再次决策的情况。

新增模块可继续使用该契约，不把轮次固定成永远相同的顺序。读取已有项目时检查前置条件；已有合格资料可以接入。

## assets.json

`assets` 数组中每份素材记录：

- `id`、`kind`、`path`、`sha256`、语言／设备、尺寸及状态。
- `source`：用户来源、采集配置、生成工具／提示词／参考、URL 与获取日期等实际适用信息。
- `usage`：reference 或 delivery；互联网与第三方素材的使用依据、署名要求和再分发范围写在 `rights`。
- `provenance`：输入素材 ID、处理方式、引擎／App 版本、job／status／manifest、输出关系。
- `editable_regions`、`fixed_regions`、焦点、完整边界、最小清晰度与替换契约。

`kind` 可使用 user、native-ui、engine-output、authored-content、generated-art、internet、font；需要其他类型时说明含义。参照证据、真实输出、艺术表达不能混称。敏感原件是否允许外发取决于本次明确授权及工具规则，不能从来源类型推断。

## 确认基准与依赖

基准保存 project 快照、已确认轮次及它们引用的素材派生链和文件哈希；未确认的候选及草稿不作为确认依赖，避免修改候选时使基准失效。基准并非复制所有大文件的备份，被引用文件需要保留可恢复的原件。`project.py snapshot` 是记录辅助工具，不判断审美，不产生授权，不自动代表所有页面完成。

当前工作状态改动后，检查相关参数、素材和输入链，列出依赖它的轮次和输出。只重新打开受影响部分，保留原用户确认作为历史证据；不得把旧基准改成新值。

换会话先核对：技能版本、当前基准、最近候选轮次、引用文件是否存在且哈希一致、未决事项、下一步和真实运行情况。恢复摘要写在项目状态中，不能依赖聊天记忆；不要把整个历史记录复制进每次对话。
