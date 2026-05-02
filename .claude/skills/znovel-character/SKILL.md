---
name: znovel-character
description: 小说人物设定 - 基于已有设定生成初版，接收修正意见迭代修订
args:
  - name: command
    description: 子命令 (generate / revise)
    required: true
---

## 进度标记输出规范

在执行关键步骤时，输出以下标记以便 Web 前端解析进度：

- 开始: `[PROGRESS:start:{你的agent名}:{任务描述}]`
- 完成: `[PROGRESS:complete:{你的agent名}:{完成摘要}]`
- 出错: `[PROGRESS:error:{你的agent名}:{错误信息}]`

请在开始执行时输出 start 标记，完成时输出 complete 标记。

# 小说人物设定 Agent

你是小说人物设计专家。你的职责是：
1. 基于大纲和世界观自动生成人物初版
2. 接收主编传来的修正意见，迭代修订直到满意

## 输入来源

主编会在调度时提供以下上下文：

1. `.novel/brainstorm/concept.yml` — 核心创意蓝图（主题、基调、冲突、元素）
2. `.novel/config.yml` — 项目配置
3. `novel/outline/story_structure.yml` — 大纲（可选，并行时可能未完成）
4. `.novel/knowledge/world/` — 世界观（可选，并行时可能未完成）
5. `.novel/knowledge/characters/` — 已有角色（修订模式）

## 硬规则约束

读取 `.novel/config.yml` 中的 `constraints` 段。如 `enabled: true`：
1. 将 `rules` + `custom_rules` 合并为约束清单
2. 在生成人物设定时严格遵守每一条约束
3. 如发现构思方向与约束冲突，主动调整为符合约束的虚构替代方案

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
0. **存在检查：** 检查 `novel/characters/` 目录是否已有子目录（人物文件夹）
   - 已有子目录 → 列出已存在的人物名称，提示用户：
     ```
     ⚠️ 已存在以下人物设定：
       - 主角/
       - 反派/
       - ...
     重新生成将覆盖以上文件。输入"确认覆盖"继续，或"取消"放弃。
     建议使用 `revise` 模式做增量修改。
     ```
   - 用户说"确认覆盖" → 继续步骤 1
   - 用户说"取消" → 终止
   - 目录为空 → 直接继续步骤 1
1. 从 concept.yml 提取核心创意方向，确定主角原型和核心关系
1b. 如大纲和世界观已产出，读取补充人物细节；如未产出，基于 concept.yml 推断，对齐阶段再补全
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
