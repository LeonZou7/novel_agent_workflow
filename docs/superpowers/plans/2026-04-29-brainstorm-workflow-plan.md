# Brainstorm-Driven Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the one-shot "generate from title" flow in outline/world/character agents with brainstorm-driven Q&A flows managed by the director.

**Architecture:** Director becomes the sole brainstorm orchestrator — it runs Q&A, persists intermediate state to `.novel/brainstorm/`, and dispatches agents as pure executors. Outline/world agents become stateless generators (structured input → files). Character agent flips to "generate first, revise via brainstorm."

**Tech Stack:** Python 3 (CLI/scripts), YAML (config/state), Markdown (skill definitions for Claude Code agents)

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `scripts/init_project.py` | Modify | Simplified init: create dirs + minimal config + brainstorm/ dir |
| `.claude/skills/novel-director.md` | Rewrite | Brainstorm orchestration for outline/world/character stages |
| `.claude/skills/novel-outline.md` | Rewrite | Pure executor: receive summary + config → generate files |
| `.claude/skills/novel-world.md` | Rewrite | Pure executor: receive summary + config + KG → generate files |
| `.claude/skills/novel-character.md` | Rewrite | Two-mode: generate initial batch → apply revision feedback |
| `tests/test_e2e.py` | Modify | Update init test for simplified config, add brainstorm dir test |

---

### Task 1: Simplify init_project.py

**Files:**
- Modify: `scripts/init_project.py`
- Modify: `tests/test_e2e.py` (test_02_config_file, test_01_directory_structure)

- [ ] **Step 1: Strip CONFIG_TEMPLATE to minimal form**

In `scripts/init_project.py`, replace the full `CONFIG_TEMPLATE` with a minimal version that only contains `project.title`. The rest of the fields will be filled during outline brainstorm.

```python
CONFIG_TEMPLATE = {
    "project": {
        "title": "",
        "type": None,
        "language": None,
    },
    "template": {
        "methodology": None,
        "custom_template_path": None,
    },
    "depth": {
        "world": "standard",
        "character": "standard",
    },
    "review": {
        "enable_proofreading": True,
        "enable_consistency": True,
        "enable_style": False,
        "style_config": {
            "chapter_target_words": 4000,
            "climax_interval_chapters": 10,
        },
    },
    "checkpoints": {
        "outline": "always",
        "world": "key_only",
        "character": "key_only",
        "draft": "every_n_chapters(10)",
        "review": "always",
    },
    "context": {
        "level1_chapters": 3,
        "level2_summary_scope": "current_arc",
        "summary_words_per_chapter": 300,
    },
    "output": {
        "base_dir": "novel",
        "chapter_filename": "ch{num}_{title}.md",
    },
}
```

- [ ] **Step 2: Remove `novel_type` parameter from `init_project()`**

Change function signature from `init_project(project_path, title, novel_type="web_novel")` to `init_project(project_path, title)`. Remove the `config["project"]["type"] = novel_type` line.

```python
def init_project(project_path: str, title: str) -> dict:
    """Initialize a novel project directory with all required files."""
    novel_root = os.path.join(project_path, NOVEL_DIR)

    if os.path.exists(novel_root):
        return {"status": "error", "message": f"Project already exists at {novel_root}"}

    knowledge_root = os.path.join(novel_root, "knowledge")
    output_root = os.path.join(project_path, CONFIG_TEMPLATE["output"]["base_dir"])

    os.makedirs(novel_root, exist_ok=True)
    os.makedirs(knowledge_root, exist_ok=True)
    os.makedirs(output_root, exist_ok=True)

    for d in KG_DIRS:
        os.makedirs(os.path.join(knowledge_root, d), exist_ok=True)

    for d in OUTPUT_DIRS:
        os.makedirs(os.path.join(output_root, d), exist_ok=True)

    # Create brainstorm directory for Q&A state persistence
    brainstorm_root = os.path.join(novel_root, "brainstorm")
    os.makedirs(brainstorm_root, exist_ok=True)

    config = copy.deepcopy(CONFIG_TEMPLATE)
    config["project"]["title"] = title

    state = copy.deepcopy(STATE_TEMPLATE)
    state["project"] = title
    state["created_at"] = datetime.now().isoformat()
    state["updated_at"] = state["created_at"]

    with open(os.path.join(novel_root, "config.yml"), "w") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    with open(os.path.join(novel_root, "state.yml"), "w") as f:
        yaml.dump(state, f, allow_unicode=True, default_flow_style=False)

    with open(os.path.join(novel_root, "work_queue.yml"), "w") as f:
        yaml.dump({"tasks": []}, f, allow_unicode=True, default_flow_style=False)

    with open(os.path.join(knowledge_root, "foreshadowing.yml"), "w") as f:
        yaml.dump({"planted": [], "progressed": [], "resolved": []}, f, allow_unicode=True, default_flow_style=False)

    with open(os.path.join(knowledge_root, "timeline.yml"), "w") as f:
        yaml.dump({"events": []}, f, allow_unicode=True, default_flow_style=False)

    # Copy bundled skills
    skills_src = os.path.join(PACKAGE_DIR, ".claude", "skills")
    skills_dst = os.path.join(project_path, ".claude", "skills")
    if os.path.isdir(skills_src):
        os.makedirs(skills_dst, exist_ok=True)
        for src_file in glob.glob(os.path.join(skills_src, "novel-*.md")):
            shutil.copy2(src_file, skills_dst)

    # Register in global project list (type is None until brainstorm determines it)
    registry = ProjectRegistry()
    registry.register(project_path, title, None)

    return {"status": "ok", "path": project_path, "title": title}
```

- [ ] **Step 3: Update CLI entry point in `__main__` block**

Remove the `[type]` argument handling:

```python
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python init_project.py <project_path> <title>")
        sys.exit(1)

    path = sys.argv[1]
    title = sys.argv[2]

    result = init_project(path, title)
    if result["status"] == "error":
        print(f"Error: {result['message']}")
        sys.exit(1)
    print(f"Project '{result['title']}' initialized at {result['path']}")
```

- [ ] **Step 4: Update `ProjectRegistry.register()` signature**

In `scripts/projects.py`, make `novel_type` optional with a default of `None`:

```python
def register(self, path: str, title: str, novel_type: str = None):
```

- [ ] **Step 5: Update test_01_directory_structure to include brainstorm/ dir**

In `tests/test_e2e.py`, add the brainstorm directory to the expected dirs list in `test_01_directory_structure`:

```python
def test_01_directory_structure(self):
    dirs = [
        ".novel",
        ".novel/knowledge",
        ".novel/knowledge/characters",
        ".novel/knowledge/world",
        ".novel/knowledge/plot",
        ".novel/knowledge/chapters",
        ".novel/brainstorm",          # NEW
        "novel",
        "novel/outline",
        "novel/world",
        "novel/characters",
        "novel/chapters",
        "novel/review",
    ]
```

- [ ] **Step 6: Update test_02_config_file to match minimal config**

```python
def test_02_config_file(self):
    import yaml
    with open(os.path.join(self.tmpdir, ".novel", "config.yml"), "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    self.assertEqual(config["project"]["title"], "E2E测试小说")
    self.assertIsNone(config["project"]["type"])       # changed
    self.assertIsNone(config["project"]["language"])    # changed
    self.assertIn("checkpoints", config)
```

- [ ] **Step 7: Update setUpClass to not pass novel_type**

```python
@classmethod
def setUpClass(cls):
    cls.tmpdir = tempfile.mkdtemp()
    init_project(cls.tmpdir, "E2E测试小说")  # removed "web_novel" arg
```

- [ ] **Step 8: Update test_09_multi_project to not pass novel_type**

```python
def test_09_multi_project(self):
    registry = ProjectRegistry()
    old_count = len(registry.list_projects())

    d2 = tempfile.mkdtemp()
    self.addCleanup(lambda: self._cleanup_project(d2))
    init_project(d2, "第二本小说")  # removed "short_story" arg

    projects = registry.list_projects()
    self.assertEqual(len(projects), old_count + 1)

    registry.unregister(d2)
    projects_after = registry.list_projects()
    self.assertEqual(len(projects_after), old_count)
```

- [ ] **Step 9: Run tests to verify changes pass**

```bash
cd /Users/leonzou/Documents/cc_novel_writer && python3 -m pytest tests/test_e2e.py -v
```

- [ ] **Step 10: Commit**

```bash
git add scripts/init_project.py scripts/projects.py tests/test_e2e.py
git commit -m "refactor: simplify init to minimal config, add brainstorm dir"
```

---

### Task 2: Rewrite novel-director.md — Outline Brainstorm Flow

**Files:**
- Modify: `.claude/skills/novel-director.md`

- [ ] **Step 1: Replace the command routing table with updated routes**

Keep the existing frontmatter, then replace the command routing table with updated routes that include brainstorm-aware flows:

```markdown
---
name: novel-director
description: 小说写作主编协调 - 脑暴问答调度、Agent调度、审核流程管理
---

# 小说写作主编协调 Agent

你是小说写作项目的主编。你负责：
1. 通过脑暴问答确定创作方向（大纲、背景设定）
2. 调度正确的 Agent 生成内容
3. 管理项目状态和审核流程
4. 在关键节点请求人工审核
5. 优先处理工作队列中的冲突

## 启动时必读

1. `.novel/config.yml` — 项目配置
2. `.novel/state.yml` — 当前运行状态
3. `.novel/work_queue.yml` — 待处理工作队列
4. `.novel/brainstorm/` — 脑暴中间状态（如有）

## 核心逻辑

### 调度优先级
```
1. 工作队列中有 pending 任务？ → 提示用户处理，询问是否先解决冲突
2. 用户指定了具体阶段？ → 进入对应阶段的脑暴→生成流程
3. 用户未指定？ → 从当前 pending 阶段继续推进
```

### 审核流程
每次 Agent 完成任务后：
1. 检查 config.checkpoints[stage]
   - `always` → 暂停，展示结果，等待用户确认
   - `key_only` → 仅大纲完成/全文完成后暂停
   - `none` → 自动推进到下一阶段
   - `every_n_chapters(N)` → 每 N 章后暂停
2. 检查工作队列是否有新任务
3. 更新 state.yml

### 配置检测
读取 config.yml 后判断：
- `config.project.type` 为 `None` → 新项目，需要脑暴确定全部配置
- `config.project.type` 已设置 → 已有项目，跳过配置问答，只做创意脑暴

## 命令路由

| 用户命令 | 行为 |
|---------|------|
| `/novel init` | 直接执行 init_project.py |
| `/novel start [stage]` | 从指定 stage 开始调度 |
| `/novel continue` | 从 current_stage 继续 |
| `/novel status` | 读取 state.yml + work_queue.yml + brainstorm/，展示状态 |
| `/novel-outline generate` | 进入大纲脑暴流程（见下方） |
| `/novel-world generate` | 进入背景设定脑暴流程（见下方） |
| `/novel-character generate` | 进入人物设定流程（生成→修正→确认） |
| `/novel-draft write <N>` | 调度 draft agent |
| `/novel-review check <N>` | 调度 review agent |
| `/novel-kg ...` | 调度 knowledge agent |
| `/novel backtrack <stage>` | 回溯处理 |
| `/novel work-queue` | 展示工作队列 |
```

- [ ] **Step 2: Add the outline brainstorm flow section**

Append after the command routing table:

```markdown

## 大纲脑暴流程 `/novel-outline generate`

### 第一步：检查脑暴状态

读取 `.novel/brainstorm/outline.yml`（如文件不存在则视为首次脑暴）：

- **status: confirmed** → 跳过脑暴，读取 `summary` 和 `config` 字段，直接跳到「调度大纲 Agent」
- **status: pending** → 展示已有问答进度，询问：「上次大纲脑暴未完成，继续还是重来？」
  - 继续：从最后一个未回答的问题继续
  - 重来：删除 outline.yml，重新开始
- **文件不存在** → 进入脑暴

### 第二步：配置问答（如 config 中 type 为 None）

逐一询问以下问题，每问一个等用户回答后写入 outline.yml（status: pending）：

**Q1: 小说类型？**
- A. 网络小说（长篇连载，爽点密集）
- B. 短篇小说（篇幅精炼，结构紧凑）

**Q2: 写作方法论？** 展示 8 种模板简要说明：

| 模板 | 适用场景 | 特点 |
|------|---------|------|
| web_trope | 金手指/升级流/打脸爽文 | 节奏快，爽点密集 |
| web_xianxia | 修仙题材 | 等级体系，机缘奇遇 |
| web_urban | 都市题材 | 现代背景，商战/异能 |
| web_romance | 言情题材 | 感情线为主 |
| three_act | 通用 | 经典三幕式结构 |
| hero_journey | 冒险/成长 | 英雄之旅 12 步 |
| save_the_cat | 商业类型片 | 15 节拍表 |
| short_story_basic | 短篇小说 | 精简结构 |

**Q3: 语言？**（默认 zh-CN）

如果 config 中 type/methodology/language 已有值，跳过对应问题。

### 第三步：核心创意问答

逐一询问：

**Q4: 核心主题 / 想表达什么？**（例：一个关于复仇与救赎的故事）

**Q5: 主角的核心冲突是什么？**（例：被灭门后隐姓埋名，在仇人麾下卧底）

**Q6: 结局走向？**（HE 圆满 / BE 悲剧 / 开放式）

**Q7: 有什么特别想包含的元素或桥段？**（可选，例：一定要有一场宗门大比）

每问一个等用户回答后更新 outline.yml。

### 第四步：输出摘要确认

脑暴完成后，汇总输出：

```
📋 大纲脑暴摘要

—— 项目配置 ——
类型：网络小说
模板：web_xianxia（修仙）
语言：zh-CN

—— 核心创意 ——
主题：……
主角冲突：……
结局走向：……
特别元素：……

是否确认以上方向？确认后大纲 Agent 将据此生成完整大纲。
```

### 第五步：确认后处理

用户确认后：
1. 将 brainstorm 中的 config 写入 `.novel/config.yml`（合并默认值）
2. 更新 `.novel/brainstorm/outline.yml` status 为 `confirmed`
3. 调度大纲 Agent，传入创意摘要

### 第六步：调度大纲 Agent

将以下结构化输入传给 outline agent：
- 创意摘要（脑暴确认的几段话）
- config.yml 路径

大纲 Agent 生成文件后：
- 展示生成结果摘要
- 按 `config.checkpoints.outline` 规则处理审核
- 更新 state.yml（outline → completed）
```

- [ ] **Step 3: Add the world brainstorm flow section**

```markdown

## 背景设定脑暴流程 `/novel-world generate`

### 第一步：检查前置条件

- 大纲脑暴是否已完成（`.novel/brainstorm/outline.yml` status: confirmed）？
  - 未完成 → 提示：「大纲脑暴尚未完成，建议先完成大纲构思。是否跳过？」
  - 用户确认跳过 → 继续

### 第二步：检查脑暴状态

读取 `.novel/brainstorm/world.yml`：

- **status: confirmed** → 跳过脑暴，读取 summary，直接调度 world agent
- **status: pending** → 提示恢复或重来
- **文件不存在** → 进入脑暴

### 第三步：核心设定问答

逐一询问，每问一个等用户回答后写入 world.yml（status: pending）：

**Q1: 世界观基调？** 提供选项参考：
- 仙侠古典 / 都市异能 / 末世废土 / 架空历史 / 科幻星际 / 西方奇幻 / 其他

**Q2: 核心力量体系方向？**
- 灵力修炼 / 科技强化 / 血脉觉醒 / 契约召唤 / 无特殊力量 / 其他

**Q3: 主要势力格局方向？**
- 正邪对立 / 多势力制衡 / 混乱无序 / 统一帝国 / 其他

**Q4: 有什么特别想包含的世界观元素？**（可选）

### 第四步：输出摘要确认

```
🌍 背景设定脑暴摘要

世界观基调：仙侠古典
力量体系：灵力修炼（修仙等级制）
势力格局：三宗四派 + 魔教对立
特别元素：上古遗迹探索

是否确认以上方向？
```

### 第五步：确认后处理

1. 更新 `.novel/brainstorm/world.yml` status 为 `confirmed`
2. 调度 world agent，传入核心设定摘要 + 大纲 KG + config

### 第六步：调度 World Agent

传入结构化输入：
- 核心设定摘要
- 大纲 KG（plot 节点）路径
- config.yml 路径

World Agent 生成文件后：
- 展示生成结果摘要
- 按 `config.checkpoints.world` 规则处理审核
- 更新 state.yml
```

- [ ] **Step 4: Add the character revision flow section**

```markdown

## 人物设定流程 `/novel-character generate`

### 第一步：检查前置条件

- 大纲脑暴是否已完成？未完成则提示可跳过
- 背景设定脑暴是否已完成？未完成则提示可跳过

### 第二步：检查脑暴状态

读取 `.novel/brainstorm/character.yml`：

- **status: confirmed** → 提示「人物设定已完成，如需修改请使用 `/novel-character revise <人物名>`」
- **status: pending** 或 **文件不存在** → 进入生成流程

### 第三步：直接调度 character agent 生成初版

读取 config.yml + 大纲 KG + 世界观 KG，将所有已有设定传给 character agent。

Character agent 输出：
- 人物列表 + 每人的 profile.md
- growth_arc.yml（如有大纲弧线）
- relationships.yml + relationship_map.yml

### 第四步：展示初版摘要，进入修正脑暴

展示人物列表（每人一行：姓名 + 角色定位 + 一句话简介），然后问：

「需要调整哪些人物？或者新增/删除人物？」

### 第五步：修正循环

用户每次提出修正意见：
1. 记录到 character.yml 的 revisions 列表
2. 将修正意见传给 character agent 进行修订
3. 展示修订结果
4. 再次询问是否需要进一步调整

循环直到用户说「可以了」或「确认」。

### 第六步：确认

- 标记 character.yml status: confirmed
- 按 `config.checkpoints.character` 规则处理审核
- 更新 state.yml
```

- [ ] **Step 5: Update the status report format to include brainstorm state**

```markdown

## 状态报告格式 `/novel status`

```
📖 《{title}》
━━━━━━━━━━━━━━━━━━━━━━
当前阶段: {current_stage}

阶段进度:
  ✅ 大纲构思    v3  (2026-04-28) [脑暴已确认]
  ✅ 背景设定    v2  (2026-04-28) [脑暴已确认]
  🔄 人物设定    v1  (进行中) [修正中，第2轮]
  ⏳ 正文编写    第 0 章
  ⏳ 审阅校对    未开始

脑暴状态:
  大纲: ✅ confirmed  背景: ✅ confirmed  人物: 🔄 pending (第2轮修正中)

工作队列: 2 个待处理
  [WQ-003] 人物等级矛盾 → character
  [WQ-004] 伏笔 V18 未推进 → outline

审核配置: 大纲 always | 正文 每10章
```
```

- [ ] **Step 6: Add brainstorm file format reference section**

```markdown

## 脑暴持久化文件格式

### `.novel/brainstorm/outline.yml`

```yaml
status: pending              # pending | confirmed
config:
  type: web_novel
  methodology: web_xianxia
  language: zh-CN
summary: |
  核心主题摘要……
questions:
  - q: "小说类型？"
    a: "网络小说"
  - q: "写作方法论？"
    a: "web_xianxia"
  - q: "语言？"
    a: "zh-CN"
  - q: "核心主题？"
    a: "……"
  - q: "主角核心冲突？"
    a: "……"
  - q: "结局走向？"
    a: "……"
  - q: "特别元素？"
    a: "……"
```

### `.novel/brainstorm/world.yml`

```yaml
status: pending
summary: |
  世界观基调摘要……
questions:
  - q: "世界观基调？"
    a: "仙侠古典"
  - q: "核心力量体系方向？"
    a: "灵力修炼"
  - q: "主要势力格局方向？"
    a: "正邪对立"
  - q: "特别想包含的世界观元素？"
    a: "上古遗迹探索"
```

### `.novel/brainstorm/character.yml`

```yaml
status: pending
revisions:
  - round: 1
    feedback: "主角性格太扁平，增加矛盾感"
    changes_made: "更新了主角 profile.md，增加内心冲突描写"
  - round: 2
    feedback: "删除配角张三"
    changes_made: "移除张三 profile，更新 relationship_map.yml"
```

## 边界情况处理

| 场景 | 处理方式 |
|------|---------|
| 脑暴中断后恢复 | 检测到 `pending`，提示「上次脑暴未完成，继续还是重来？」 |
| 已确认后想推翻 | 用户说「重新确定」，将 status 重置为 `pending`，清空 questions，重新脑暴 |
| 跳过前置阶段 | 提示「XX 尚未确定，建议先完成，是否跳过？」 |
| 脑暴中改变主意 | 用户说「回到上个问题」，回到上一个问答 |
| Agent 生成结果不满意 | 回到摘要确认环节，重新确认方向后再次生成 |
| 已有项目（config 完整） | 跳过配置问答（Q1-Q3），只做创意脑暴（Q4-Q7） |
```

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/novel-director.md
git commit -m "refactor: rewrite director with brainstorm orchestration flow"
```

---

### Task 3: Simplify novel-outline.md to Pure Executor

**Files:**
- Modify: `.claude/skills/novel-outline.md`

- [ ] **Step 1: Replace the entire file content**

The outline agent becomes a pure executor — it receives a structured creative summary from the director and generates files. No more creative questioning.

```markdown
---
name: novel-outline
description: 小说大纲构思 - 接收创意摘要，生成情节大纲、卷章结构、节奏规划
---

# 小说大纲构思 Agent

你是小说大纲构思专家。你的职责是根据主编提供的创意摘要和项目配置，生成完整的故事大纲。

## 输入来源

主编会传入以下结构化输入（在调度时提供）：

1. **创意摘要**：一段或多段话，描述核心主题、主角冲突、结局走向、特别元素
2. `.novel/config.yml` — 项目配置（模板选择、类型、语言）
3. `.novel/knowledge/plot/` — 已生成的情节节点（如为修订模式）
4. `.novel/knowledge/characters/` — 已有人物设定（如有）
5. `.novel/knowledge/world/` — 已有世界观设定（如有）
6. `templates/{methodology}.yml` — 选定的写作模板

## 输出产物

生成以下文件到 `novel/outline/`：

### story_structure.yml
```yaml
title: "小说标题"
type: web_novel
total_chapters_estimate: 300
arcs:
  - name: "第一卷：崛起"
    chapters: "1-100"
    summary: "主轴概述"
    key_events:
      - chapter: 1
        event: "简述关键事件"
```

### chapter_outlines/
每章一个文件 `ch{N}_outline.md`，包含 300-500 字情节梗概。

### rhythm_map.yml
```yaml
chapter: 1
beat_type: setup         # setup | buildup | climax | resolution | cliffhanger
tension_level: 3         # 1-10
key_emotion: "期待"
```

## 生成规范

1. 严格按照创意摘要中确定的方向展开，不自行偏离核心主题和结局走向
2. 根据模板的结构节拍分配卷弧和章节
3. 网络小说类型注意每章结尾留悬念/爽点
4. 短篇小说类型注意结构紧凑，控制章节总数

## 写入 KG 规范

每次生成/修改后，将以下信息写入 KG：
- 情节节点 → `.novel/knowledge/plot/{arc_name}.yml`
- 伏笔意图 → `.novel/knowledge/foreshadowing.yml` 的 planted 列表

情节节点格式：
```yaml
name: "弧名"
chapter_range: "1-30"
summary: "弧线概述"
key_plot_points:
  - chapter: 1
    event: "事件描述"
    type: setup
foreshadowing_planted: []
```

## 工作模式

### generate — 从创意摘要生成
1. 读取主编传入的创意摘要 + config + 模板
2. 根据模板结构节拍，生成卷弧划分和章节大纲
3. 输出 story_structure.yml + chapter_outlines/ + rhythm_map.yml
4. 将关键情节节点写入 `.novel/knowledge/plot/`
5. 更新 `.novel/knowledge/foreshadowing.yml` 记录伏笔意图

### revise — 修订已有大纲
1. 读取用户指定的文件
2. 根据用户指令修改
3. 如修改涉及 KG 条目，同步更新 KG
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/novel-outline.md
git commit -m "refactor: simplify outline agent to pure executor"
```

---

### Task 4: Simplify novel-world.md to Pure Executor

**Files:**
- Modify: `.claude/skills/novel-world.md`

- [ ] **Step 1: Replace the entire file content**

Same pattern as outline — remove creative questioning, receive structured summary from director.

```markdown
---
name: novel-world
description: 小说背景设定 - 接收核心设定摘要，生成世界观、地理、历史、势力、力量体系
---

# 小说背景设定 Agent

你是小说世界观构建专家。你的职责是根据主编提供的核心设定摘要和大纲情节需求，构建完整且自洽的世界设定。

## 输入来源

主编会传入以下结构化输入：

1. **核心设定摘要**：世界观基调、力量体系方向、势力格局方向、特别元素
2. `.novel/config.yml` — 项目配置
3. `novel/outline/story_structure.yml` — 大纲中的场景需求
4. `.novel/knowledge/world/` — 已有世界观条目
5. `.novel/knowledge/plot/` — 情节节点（了解需要什么设定）

## 输出产物

根据核心设定摘要和情节需求自行决定产出详细程度：

- `novel/world/overview.md` — 世界观总览（500-800 字）
- `novel/world/geography.md` — 地理概述
- `novel/world/history_timeline.yml` — 历史大事年表
- `novel/world/power_system.md` — 力量体系详述
- `novel/world/factions.md` — 主要势力/组织

## 世界观构建框架

生成时覆盖以下维度：

1. **时空背景**：时代、世界形态（架空/历史/现代/未来）
2. **地理环境**：主要区域、气候、资源分布
3. **社会结构**：阶级、种族、文明、文化特色
4. **力量体系**（如有）：等级划分、获取方式、限制规则
5. **历史脉络**：关键历史事件及其对当前世界的影响
6. **势力格局**：主要组织/势力及其关系

## 写入 KG 规范

每个设定维度作为一个独立条目写入：
- → `.novel/knowledge/world/overview.yml`
- → `.novel/knowledge/world/power_system.yml`
- → `.novel/knowledge/world/geography.yml`
- → `.novel/knowledge/world/factions.yml`
- → `.novel/knowledge/world/history.yml`

条目格式：
```yaml
name: "条目名"
category: world
summary: "一句话概述"
details: |
  详细内容...
relationships:
  - target: "相关条目名"
    relation: "describes | belongs_to | conflicts_with"
```

## 工作模式

### generate — 从核心摘要生成
1. 读取主编传入的核心设定摘要 + 大纲 KG + config
2. 根据摘要确定的方向生成各维度设定
3. 输出 Markdown 文件到 novel/world/
4. 将结构化摘要写入 KG

### revise — 修订已有设定
1. 读取指定条目
2. 根据用户指令修改
3. 更新 KG 对应条目，记录版本变化
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/novel-world.md
git commit -m "refactor: simplify world agent to pure executor"
```

---

### Task 5: Restructure novel-character.md to Two-Mode

**Files:**
- Modify: `.claude/skills/novel-character.md`

- [ ] **Step 1: Replace the entire file content**

Character agent flips to "generate first, revise via feedback." Two modes: generate initial batch from all available settings, and apply revision feedback.

```markdown
---
name: novel-character
description: 小说人物设定 - 基于已有设定生成初版，接收修正意见迭代修订
---

# 小说人物设定 Agent

你是小说人物设计专家。你的职责是：
1. 基于大纲和世界观自动生成人物初版
2. 接收主编传来的修正意见，迭代修订直到满意

## 输入来源

主编会在调度时提供以下上下文：

1. `.novel/config.yml` — 项目配置
2. `novel/outline/story_structure.yml` — 大纲（角色需求来源）
3. `.novel/knowledge/world/` — 世界观（角色所处的环境）
4. `.novel/knowledge/characters/` — 已有角色（修订模式）
5. `.novel/knowledge/plot/` — 情节节点

## 输出产物

### 每个人物 → `novel/characters/{name}/`

**profile.md**:
```markdown
# {人物名}

## 基本信息
- 姓名/别名：
- 性别/年龄：
- 身份/职业：
- 外貌特征：

## 性格
- 核心性格：
- 优点：
- 缺点/弱点：
- 口头禅/习惯动作：

## 背景故事
- 出身：
- 关键经历：
- 核心动机/目标：
```

**growth_arc.yml**:
```yaml
character: "林风"
arcs:
  - arc: "第一卷"
    start_state: "胆小怯懦的废柴少年"
    end_state: "初具信心的筑基修士"
    key_growth_events:
      - chapter: 10
        event: "第一次独自击败妖兽"
        growth: "获得自信"
```

**relationships.yml**:
```yaml
character: "林风"
relationships:
  - target: "苏小婉"
    type: "道侣/红颜"
    development: "从误会到信任到感情"
    key_chapters: [5, 20, 50]
```

### 全角色关系图 → `novel/characters/relationship_map.yml`

## 写入 KG 规范

每个人物写入 → `.novel/knowledge/characters/{name}.yml`:

```yaml
name: "林风"
aliases: ["小林", "风哥"]
role: protagonist             # protagonist | antagonist | supporting | minor
status: active
current_level: "筑基初期"
faction: "天剑宗"
key_traits: ["坚韧", "谨慎", "重情义"]
key_relationships:
  - name: "苏小婉"
    relation: "道侣"
    status: "发展中"
appears_in: []
growth_summary: "从废柴到强者"
```

## 工作模式

### generate — 从已有设定生成初版
1. 从大纲提取所有需要人物的场景
2. 识别主角、反派、重要配角、功能性角色
3. 根据世界观设定为每个角色匹配合适的背景、能力和关系
4. 生成所有人物档案、成长弧线、关系网
5. 写入 KG

### revise — 根据主编反馈修订
主编会传入具体的修正意见（可能包含多轮反馈中的最新一轮）。你需要：
1. 读取已有的人物文件
2. 根据修正意见修改指定人物的属性/关系/弧线
3. 如果修改涉及关系变化，同步更新 relationship_map.yml
4. 更新 KG 对应条目
5. 如果删除人物，移除对应文件和 KG 条目，并清理其他人物关系中的引用

修正意见示例：
- "主角性格太扁平，增加内心矛盾"
- "删除配角张三"
- "新增一个人物：李四，主角的师兄，亦敌亦友"
- "把女主角从温柔型改成御姐型"
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/novel-character.md
git commit -m "refactor: restructure character agent for generate-first-then-revise flow"
```

---

### Task 6: Update Tests for Brainstorm Directory

**Files:**
- Modify: `tests/test_e2e.py`

- [ ] **Step 1: Add test for brainstorm directory and outline.yml**

Add a new test after `test_01_directory_structure`:

```python
def test_01b_brainstorm_directory(self):
    """Verify brainstorm/ directory is empty and ready for use."""
    import yaml

    brainstorm_dir = os.path.join(self.tmpdir, ".novel", "brainstorm")
    self.assertTrue(os.path.isdir(brainstorm_dir))

    # Verify no stale brainstorm files exist
    outline_path = os.path.join(brainstorm_dir, "outline.yml")
    world_path = os.path.join(brainstorm_dir, "world.yml")
    character_path = os.path.join(brainstorm_dir, "character.yml")
    self.assertFalse(os.path.exists(outline_path))
    self.assertFalse(os.path.exists(world_path))
    self.assertFalse(os.path.exists(character_path))
```

- [ ] **Step 2: Add test for outline.yml read/write as director would do**

```python
def test_01c_brainstorm_outline_yml(self):
    """Test the brainstorm outline.yml lifecycle: pending → confirmed."""
    import yaml

    outline_path = os.path.join(self.tmpdir, ".novel", "brainstorm", "outline.yml")

    # Simulate director starting brainstorm
    brainstorm = {
        "status": "pending",
        "config": {
            "type": "web_novel",
            "methodology": "web_xianxia",
            "language": "zh-CN",
        },
        "summary": "",
        "questions": [
            {"q": "小说类型？", "a": "网络小说"},
        ],
    }
    with open(outline_path, "w", encoding="utf-8") as f:
        yaml.dump(brainstorm, f, allow_unicode=True, default_flow_style=False)

    # Verify pending state
    with open(outline_path, "r", encoding="utf-8") as f:
        saved = yaml.safe_load(f)
    self.assertEqual(saved["status"], "pending")
    self.assertEqual(saved["config"]["type"], "web_novel")

    # Simulate user confirming
    saved["status"] = "confirmed"
    saved["summary"] = "一个关于复仇与成长的修仙故事……"
    saved["questions"].extend([
        {"q": "写作方法论？", "a": "web_xianxia"},
        {"q": "语言？", "a": "zh-CN"},
        {"q": "核心主题？", "a": "复仇与成长"},
        {"q": "主角核心冲突？", "a": "卧底仇人门下"},
        {"q": "结局走向？", "a": "HE"},
        {"q": "特别元素？", "a": "宗门大比"},
    ])
    with open(outline_path, "w", encoding="utf-8") as f:
        yaml.dump(saved, f, allow_unicode=True, default_flow_style=False)

    # Verify confirmed state
    with open(outline_path, "r", encoding="utf-8") as f:
        confirmed = yaml.safe_load(f)
    self.assertEqual(confirmed["status"], "confirmed")
    self.assertEqual(len(confirmed["questions"]), 7)
    self.assertIsNotNone(confirmed["summary"])
```

- [ ] **Step 3: Run all tests**

```bash
cd /Users/leonzou/Documents/cc_novel_writer && python3 -m pytest tests/test_e2e.py -v
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_e2e.py
git commit -m "test: add brainstorm directory and outline.yml lifecycle tests"
```

---

### Task 7: End-to-End Verification

**Files:** None (verification only)

- [ ] **Step 1: Verify init creates correct minimal structure**

```bash
cd /tmp && rm -rf test-novel && python3 /Users/leonzou/Documents/cc_novel_writer/scripts/init_project.py test-novel "测试小说"
```

Check that:
- `test-novel/.novel/config.yml` has `type: null` and `language: null`
- `test-novel/.novel/brainstorm/` directory exists and is empty
- No errors during init

- [ ] **Step 2: Check all skill files have valid YAML frontmatter**

```bash
cd /Users/leonzou/Documents/cc_novel_writer
for f in .claude/skills/novel-*.md; do
  echo "=== $f ==="
  head -5 "$f"
done
```

Verify each has `---`, `name:`, `description:` lines.

- [ ] **Step 3: Run full test suite**

```bash
cd /Users/leonzou/Documents/cc_novel_writer && python3 -m pytest tests/ -v
```

Expected: all 11 tests pass (9 original + 2 new).

- [ ] **Step 4: Clean up test project**

```bash
rm -rf /tmp/test-novel
```

- [ ] **Step 5: Final commit (if any cleanup needed)**

```bash
git status
```
```

---

## Self-Review

**1. Spec coverage check:**
- Section 1.1 (Outline brainstorm flow) → Task 2 Steps 2, 5, 6
- Section 1.2 (World brainstorm flow) → Task 2 Step 3
- Section 1.3 (Character revision flow) → Task 2 Step 4
- Section 2 (Init simplification) → Task 1 Steps 1-3
- Section 3 (Brainstorm persistence) → Task 1 Step 2 (dir creation), Task 2 Step 6 (file formats), Task 6 (tests)
- Section 4 (Edge cases) → Task 2 Step 6 (edge case table)
- Section 5 (Files to change) → All 5 files covered across Tasks 1-5
- Section 6 (Backward compatibility) → Task 2 Step 1 (config detection), Step 6 (edge case: existing project)

**2. Placeholder scan:** No TBD, TODO, or vague instructions. All steps have concrete code or markdown content.

**3. Type consistency:** 
- `outline.yml` status field: `pending | confirmed` — consistent across Tasks 2 and 6
- `brainstorm/` directory path: `.novel/brainstorm/` — consistent across all tasks
- `init_project()` signature: `(project_path, title)` without `novel_type` — consistent in Task 1 and test updates
