# 脑暴式写作工作流 — 设计规格

## 概述

将大纲构思、背景设定、人物设定三个阶段的 Agent 工作流改为脑暴对话驱动：
- **大纲构思** & **背景设定**：先通过问答确定核心方向，再让 agent 生成文件
- **人物设定**：agent 先基于已有设定输出初版，再通过脑暴对话修正

同时将 `init` 命令简化，项目配置（类型、模板、语言等）不再在 init 时确定，而是在脑暴过程中一并收集并持久化。

---

## 1. Director 脑暴流程

### 1.1 大纲构思

```
用户: /novel-outline generate
        ↓
Director: 检查 .novel/brainstorm/outline.yml
  - 已 confirmed → 跳过脑暴，直接调度 outline agent
  - 已 pending → 提示「上次脑暴未完成，继续还是重来？」
  - 不存在 → 进入脑暴
        ↓
Director: 脑暴问答（两组）
  第一组：项目配置
    Q1: 类型？（网络小说 / 短篇小说）
    Q2: 写作方法论？（展示 8 种模板简要说明供选择）
    Q3: 语言？
  
  第二组：核心创意
    Q4: 核心主题 / 想表达什么？
    Q5: 主角的核心冲突是什么？
    Q6: 结局走向（HE / BE / 开放式）？
    Q7: 有什么特别想包含的元素或桥段？
        ↓
Director 输出：
  ① config 预览（类型、模板、语言）
  ② 创意摘要（几段话）
  请用户确认
        ↓
用户确认 → Director 写入 config.yml + outline.yml（status: confirmed）
        → 调度 outline agent，传入创意摘要 + config
        ↓
Outline Agent: 接收结构化输入，生成：
  - novel/outline/story_structure.yml
  - novel/outline/chapter_outlines/
  - novel/outline/rhythm_map.yml
        ↓
Director: 展示结果，按 checkpoints.outline 规则处理审核
```

### 1.2 背景设定

```
用户: /novel-world generate
        ↓
Director: 检查 .novel/brainstorm/world.yml
  - 已 confirmed → 跳过脑暴，直接调度 world agent
  - 已 pending → 提示恢复或重来
  - 不存在 → 检查大纲脑暴是否完成，未完成则提示，进入脑暴
        ↓
Director: 脑暴问答
  Q1: 世界观基调？（如：仙侠古典 / 都市异能 / 末世废土 / 架空历史...）
  Q2: 核心力量体系方向？（如：灵力修炼 / 科技强化 / 血脉觉醒 / 契约召唤...）
  Q3: 主要势力格局方向？（如：正邪对立 / 多势力制衡 / 混乱无序...）
  Q4: 有什么特别想包含的世界观元素？（可选）
        ↓
Director 输出：核心设定摘要（几段话），请用户确认
        ↓
用户确认 → Director 写入 world.yml（status: confirmed）
        → 调度 world agent，传入核心设定摘要 + 大纲 KG + config
        ↓
World Agent: 生成：
  - novel/world/overview.md
  - novel/world/geography.md
  - novel/world/history_timeline.yml
  - novel/world/power_system.md
  - novel/world/factions.md
        ↓
Director: 展示结果，按 checkpoints.world 规则处理审核
```

### 1.3 人物设定

```
用户: /novel-character generate
        ↓
Director: 检查 .novel/brainstorm/character.yml
  - 不存在或 pending → 进入流程
  - 已 confirmed → 跳过，提示已完成
        ↓
Director: 读取 config.yml + 大纲 KG + 世界观 KG
        → 直接调度 character agent
        ↓
Character Agent: 基于已有设定输出初版：
  - 人物列表 + profile.md
  - growth_arc.yml
  - relationships.yml + relationship_map.yml
        ↓
Director: 展示初版摘要（人物列表 + 一句话简介），进入修正脑暴
  "需要调整哪些人物？或者新增/删除人物？"
        ↓
用户逐项提出修正 → 写入 character.yml 修订记录
  → Character Agent 根据修正意见修订文件
  → 可多轮，直到用户说「可以了」
        ↓
Director: 标记 character.yml status: confirmed
        → 按 checkpoints.character 规则处理审核
```

---

## 2. init 命令简化

`novelwriting init <path> <title>` 改为：

- 创建项目目录结构（`.novel/`、`novel/`）
- 写入 `.novel/config.yml`（只含 `project.title`，其余字段留空或默认值）
- 注册到 `~/.novel/projects.yml`
- 不再进行交互式问卷

类型、模板、语言等配置全部挪到脑暴阶段确定。

---

## 3. 脑暴持久化

新增 `.novel/brainstorm/` 目录存放脑暴中间状态：

```
.novel/brainstorm/
├── outline.yml      # 大纲脑暴结论（配置 + 创意摘要）
├── world.yml        # 背景设定脑暴结论
└── character.yml    # 人物修正记录
```

### outline.yml 结构

```yaml
status: confirmed              # pending | confirmed
config:
  type: web_novel
  methodology: web_xianxia
  language: zh-CN
summary: |
  核心主题摘要……
questions:                     # 记录每个问答，用于恢复
  - q: "核心主题？"
    a: "复仇与成长"
  - q: "主角核心冲突？"
    a: "……"
```

### world.yml 结构

```yaml
status: confirmed
summary: |
  世界观基调摘要……
questions:
  - q: "世界观基调？"
    a: "仙侠古典"
  # ...
```

### character.yml 结构

```yaml
status: confirmed
revisions:                     # 修正记录列表
  - round: 1
    feedback: "主角性格太扁平，增加矛盾感"
    changes_made: "更新了主角 profile.md，增加内心冲突描写"
  - round: 2
    feedback: "删除配角张三"
    changes_made: "移除张三 profile，更新 relationship_map.yml"
```

### 作用

- **中断恢复**：Director 启动时检查状态，`pending` 则提示继续或重来
- **跳过已完成**：`confirmed` 状态跳过脑暴，直接调度 agent
- **上下文传递**：后续阶段脑暴时读取前序结论（如背景设定脑暴参考大纲结论）

---

## 4. 边界情况处理

| 场景 | 处理方式 |
|------|---------|
| 脑暴中断后恢复 | 检测到 `pending`，提示「上次脑暴未完成，继续还是重来？」 |
| 已确认后想推翻 | 用户说「重新确定」，Director 重置状态为 `pending`，重新脑暴 |
| 跳过背景直接写人物 | 提示「背景设定尚未确定，建议先完成，是否跳过？」 |
| 脑暴中改变主意 | 用户说「回到上个问题」，Director 回到上一个问答 |
| Agent 生成结果不满意 | 回到脑暴摘要确认环节，重新确认方向后再次生成 |

---

## 5. 涉及改动的文件

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `.claude/skills/novel-director.md` | 重写 | 新增脑暴对话逻辑，调度前检查 brainstorm/ 目录 |
| `.claude/skills/novel-outline.md` | 改为纯执行 | 接收结构化输入 → 生成文件，移除自主创意发挥 |
| `.claude/skills/novel-world.md` | 改为纯执行 | 同上 |
| `.claude/skills/novel-character.md` | 重构 | 初版生成 → 接收修正意见 → 修订，支持多轮 |
| `scripts/init_project.py` | 简化 | 只创建目录 + 写入标题 + 注册，移除交互问卷 |
| `.novel/brainstorm/` | 新增 | 脑暴中间状态存储目录 |

---

## 6. 约束与上游兼容

- 已有项目的 `.novel/config.yml` 不受影响——Director 检测到已有完整 config 时跳过配置问答，只做创意脑暴
- 已有项目无 `brainstorm/` 目录时视为首次脑暴，正常进入流程
- `--depth` 参数从 world 和 character 命令中移除，agent 自行决定产出详细程度
- 写作模板文件（`templates/*.yml`）不变
