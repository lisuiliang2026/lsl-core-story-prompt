# 00故事核心提示词 · lsl core story prompt

在**剧本**和**导演 skill（director-video-prompt）**之间加一个前置环节：先定这一集的核心、每一段的核心，把“这部戏怎么演、按时间怎么排”具体到人、物、场景、秒数，让人看得懂、能参与，再整包交给导演 skill。

- **当前**：skill v0.1.0 · 方法论 v0.1 · 界面基线 CSP-UI-1 · 宪法 v1（2026-11-07）。
- **工作台**：https://claude.ai/artifact/Fq7iWeUHqQ8WKvh35uLVCo。

## 先读哪几份

1. `进度.md`：现在停在哪、下一步、等你的事（每次对话先读）。
2. `项目宪法.md`：项目怎么推进、方法论怎么升级、质检、界面、发版、红线。
3. `推进计划.md`：P0—P5 各阶段要交出什么。
4. `lsl-core-story-prompt/SKILL.md`：skill 本体。

## 文件夹

```
00故事核心提示词/
  README.md            本文件
  项目宪法.md           推进规则（宪法 v1）
  推进计划.md           阶段计划
  进度.md               状态板
  方法论台账.md         M 方法 / U 界面 / F 失败样本
  lsl-core-story-prompt/     ← skill 本体（安装包从这里打）
    SKILL.md
    CHANGELOG.md
    references/        method 方法 · templates 句式模板 · qa 质检规则 · output 输出与交接 · example-mengfusheng 示例
    ui-baseline/       界面基线 CSP-UI-1：web/workbench.html、样例数据、tests、截图
    tools/qa_check.py  Q1 质检脚本
  案例/                 每个剧本一个文件夹：案例卡、质检报告
  质检/                 质检报告模板
  推送/                 双击推送.bat、push.ps1、repo.txt、msg/（每版的提交说明）
  安装包/               lsl-core-story-prompt_vX.Y.Z.zip（不进仓库）
```

## 怎么推到 GitHub

1. 在 GitHub 建私有仓库（推荐名 `lsl-core-story-prompt`）。地址和 `推送/repo.txt` 里的不一样，就改那一行。
2. 开 Clash，双击 `推送/双击推送.bat`。
3. 看到提交列表，输入 `Y`。
4. 最后一行是 `DONE. Pushed main and tag vX.Y.Z` 就成了，截图发回来。

脚本不会强推：远端有本机没有的提交就停下来；已经推过的版本会直接说 `Already done`。
