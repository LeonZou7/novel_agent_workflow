# Novel Writer — 小说写作工作流

基于 Claude Code Agent 体系的小说写作自动化工具。覆盖大纲构思、背景设定、人物设定、正文编写到审阅校对五个环节，大纲和背景设定通过脑暴问答确定方向后由 Agent 生成，人物设定先生成初版再脑暴修正，关键节点支持人工审核。

## 快速开始

### 安装

将此目录加入 PATH（一次性操作）：

```bash
echo 'export PATH="$PATH:'$(pwd)'"' >> ~/.zshrc
source ~/.zshrc
```

依赖安装：

```bash
pip3 install pyyaml flask
```

安装 Claude Code 技能（符号链接到 `~/.claude/skills/`，修改仓库中的技能后自动生效）：

```bash
novelwriting install-skills
```

### 创建第一个项目

```bash
novelwriting init ./my-novel "剑破苍穹"
cd my-novel
```

项目结构：

```
my-novel/
├── .novel/                    # 项目数据
│   ├── config.yml             #   配置
│   ├── state.yml              #   运行状态
│   ├── work_queue.yml         #   审阅工作队列
│   ├── brainstorm/             #   脑暴中间状态
│   │   ├── outline.yml         #     大纲脑暴结论
│   │   ├── world.yml           #     背景设定脑暴结论
│   │   └── character.yml       #     人物修正记录
│   └── knowledge/             #   知识图谱（设定真相源）
│       ├── characters/        #     人物条目
│       ├── world/             #     世界观条目
│       ├── plot/              #     情节节点
│       ├── chapters/          #     章节摘要
│       ├── foreshadowing.yml  #     伏笔追踪
│       └── timeline.yml       #     大事年表
├── .claude/skills/            # Claude Code Agent 技能（自动复制）
│   ├── novel-director/SKILL.md
│   ├── novel-outline/SKILL.md
│   ├── novel-world/SKILL.md
│   ├── novel-character/SKILL.md
│   ├── novel-draft/SKILL.md
│   ├── novel-review/SKILL.md
│   └── novel-kg/SKILL.md
└── novel/                     # 写作产物
    ├── outline/               #   大纲
    ├── world/                 #   背景设定
    ├── characters/            #   人物设定
    ├── chapters/              #   正文
    └── review/                #   审阅报告
```

## CLI 命令

| 命令 | 用途 |
|------|------|
| `novelwriting init <path> <title>` | 创建新小说项目 |
| `novelwriting install-skills` | 将 novel-* 技能符号链接到 `~/.claude/skills/` |
| `novelwriting serve` | 启动 Web 界面 |
| `novelwriting list` | 列出所有已注册项目 |
| `novelwriting status [path]` | 查看项目阶段进度 |

类型和模板在后续脑暴问答中确定，不再在 `init` 时指定。

## Web 界面

```bash
novelwriting serve
# → 打开 http://localhost:8080
```

功能页面：

- **仪表盘**：项目进度概览、工作队列
- **命令中心**：一键复制 `/novel-*` 命令到 Claude Code 终端执行
- **大纲 / 人物 / 世界观 / 正文 / 审阅**：查看各阶段产物

页面左上角下拉框可切换已注册的项目。

## Claude Code 工作流

首次使用前先安装技能：`novelwriting install-skills`（或在项目目录下运行 `novelwriting init`，技能会自动复制到项目中）。

在项目目录中使用 `/` 命令驱动各阶段 Agent。

| 命令 | Agent | 流程 |
|------|-------|------|
| `/novel-outline generate` | 大纲构思 | 脑暴问答确定方向 → agent 生成文件 |
| `/novel-world generate` | 背景设定 | 脑暴问答确定方向 → agent 生成文件 |
| `/novel-character generate` | 人物设定 | agent 生成初版 → 脑暴对话修正迭代 |
| `/novel-draft write <N>` | 正文编写 | 按大纲和三层上下文写第 N 章 |
| `/novel-review check <N>` | 审阅校对 | 多维度检查第 N 章质量 |
| `/novel status` | 主编协调 | 查看项目整体状态（含脑暴进度） |
| `/novel work-queue` | 主编协调 | 查看审阅发现的待处理问题 |
| `/novel-kg query "..."` | 知识管理 | 自然语言查询知识图谱 |

### 工作流顺序

```
脑暴大纲 → 脑暴背景 → 生成人物初版 → 脑暴修正人物 → 正文编写 → 审阅校对
                ↑                                                    ↓
                └──────────── 问题回调修订 ──────────────────────────┘
```

### 审核配置

在 `.novel/config.yml` 中调整各阶段审核模式：

```yaml
checkpoints:
  outline: always              # always | key_only | none
  world: key_only
  character: key_only
  draft: every_n_chapters(10)  # every_n_chapters(N)
  review: always
```

## 知识图谱

所有设定存储在 `.novel/knowledge/` 中，作为各 Agent 的共享真相源。写第 N 章时，draft Agent 自动获取三层压缩上下文：

- **Level 1**（~12K tokens）：最近 3 章完整正文
- **Level 2**（~8K tokens）：当前弧的章节摘要 + 伏笔追踪表
- **Level 3**（~5K tokens）：全局人物档案 + 世界观摘要 + 大事年表

每章写完后自动更新 KG 摘要，旧章节全文归档。

## 写作模板

内置 8 种写作方法论模板，在大纲脑暴问答中选择：

- `web_trope` — 金手指/升级流
- `web_xianxia` — 修仙
- `web_urban` — 都市
- `web_romance` — 言情
- `three_act` — 经典三幕式
- `hero_journey` — 英雄之旅
- `save_the_cat` — Save the Cat! 节拍表
- `short_story_basic` — 短篇小说基础

## 技能开发

技能文件位于 `.claude/skills/novel-*/SKILL.md`，与项目代码一同版本控制。修改后：

- 项目内的技能：`novelwriting init` 的项目会使用复制的版本
- 全局安装的技能：通过 `install-skills` 创建的符号链接自动指向仓库，无需重新安装

```
.claude/skills/
├── novel-director/SKILL.md    # 主编协调
├── novel-outline/SKILL.md     # 大纲构思
├── novel-world/SKILL.md       # 背景设定
├── novel-character/SKILL.md   # 人物设定
├── novel-draft/SKILL.md       # 正文编写
├── novel-review/SKILL.md      # 审阅校对
└── novel-kg/SKILL.md          # 知识图谱管理
```

## 全局项目注册表

所有项目登记在 `~/.novel/projects.yml` 中，`init` 时自动注册。Web 界面基于注册表展示多项目列表。
