# Novel Writer — 小说写作工作流

基于 Claude Code Agent 体系的小说写作自动化工具。覆盖大纲构思、背景设定、人物设定、正文编写到审阅校对五个环节，每个环节由独立 Agent 负责，关键节点支持人工审核。

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
│   └── knowledge/             #   知识图谱（设定真相源）
│       ├── characters/        #     人物条目
│       ├── world/             #     世界观条目
│       ├── plot/              #     情节节点
│       ├── chapters/          #     章节摘要
│       ├── foreshadowing.yml  #     伏笔追踪
│       └── timeline.yml       #     大事年表
├── .claude/skills/            # Claude Code Agent 技能（自动复制）
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
| `novelwriting init <path> <title> [type]` | 创建新小说项目 |
| `novelwriting serve` | 启动 Web 界面 |
| `novelwriting list` | 列出所有已注册项目 |
| `novelwriting status [path]` | 查看项目阶段进度 |

`type` 可选值：`web_novel`（默认，网络小说）、`short_story`（短篇小说）。

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

在项目目录中使用 `/` 命令驱动各阶段 Agent：

| 命令 | Agent | 功能 |
|------|-------|------|
| `/novel-outline generate` | 大纲构思 | 生成情节大纲、卷章结构、节奏规划 |
| `/novel-world generate [--depth]` | 背景设定 | 生成世界观、地理、历史、势力、力量体系 |
| `/novel-character generate [--depth]` | 人物设定 | 生成人物档案、关系网、成长弧线 |
| `/novel-draft write <N>` | 正文编写 | 按大纲和三层上下文写第 N 章 |
| `/novel-review check <N>` | 审阅校对 | 多维度检查第 N 章质量 |
| `/novel status` | 主编协调 | 查看项目整体状态 |
| `/novel work-queue` | 主编协调 | 查看审阅发现的待处理问题 |
| `/novel-kg query "..."` | 知识管理 | 自然语言查询知识图谱 |

### 工作流顺序

```
大纲构思 → 背景设定 → 人物设定 → 正文编写 → 审阅校对
   ↑                                    ↓
   └──────── 问题回调修订 ──────────────┘
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

内置 8 种写作方法论模板，在 `config.yml` 中选择：

- `web_trope` — 金手指/升级流
- `web_xianxia` — 修仙
- `web_urban` — 都市
- `web_romance` — 言情
- `three_act` — 经典三幕式
- `hero_journey` — 英雄之旅
- `save_the_cat` — Save the Cat! 节拍表
- `short_story_basic` — 短篇小说基础

## 全局项目注册表

所有项目登记在 `~/.novel/projects.yml` 中，`init` 时自动注册。Web 界面基于注册表展示多项目列表。
