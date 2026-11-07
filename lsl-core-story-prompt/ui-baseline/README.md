# ui-baseline（界面基线）· 用法

当前基线：**CSP-UI-1**（清单、数据、交互规则见 `CSP-UI-1.md`，截图见 `screenshots/`）。目的：每个项目用同一个剧情核心工作台，不靠各对话自己重做。

## 文件夹

```
ui-baseline/
  CSP-UI-1.md                 界面清单、用户原话、数据结构、按钮文字、自检、怎么升级
  README.md                   本文件
  web/workbench.html          工作台页面（单文件，发布时声明 db、sample、downloads）
  example-mengfusheng/
    seed.json                 《梦浮生》第 01 集样例：项目 + 10 个检查点
    make_seed.py              重新生成 seed.json
  tests/
    mock.js                   假 Claude（内存数据库、固定回答、假下载）
    build.py                  拼本地测试页 → tests/out/index.html
    test_page.js              浏览器实测 27 条；--shots 重拍截图
  screenshots/                01 页首 · 02 段核心 · 03 四张表 · 04 节拍 · 05 提示词 · 06 手机
```

## 新项目怎么开

1. **发布页面**：用 Artifact 发布 `web/workbench.html`，`capabilities: {"db": {}, "sample": {}, "downloads": true}`，图标 `graph`。一个剧作开一个页面也行，几个项目共用一个页面也行（页面里有项目下拉）。
2. **建项目**：
   - 一般让用户在页面里点“新建项目”，粘贴剧本。页面会自己调 Claude 读剧本，第一次调用时请用户同意。
   - 也可以由 Claude 先写好档案：用 ArtifactData `set projects/<id>`，内容是 `{title, updatedAt, json}`，格式见 `CSP-UI-1.md` 第六节。
3. **要样例时**：把 `example-mengfusheng/seed.json` 写进去。
   - `project` 写到 `projects/mengfusheng`。
   - `checkpoints[i]` 依次写到 `projects/mengfusheng/checkpoints/c01…c10`。
   - 一次 batch 写完。
4. **质检**：用 ArtifactData `get projects/<id>` 存成文件，跑 `python3 ../tools/qa_check.py 文件 --out 报告.md`。

## 不要做的事

- 不在项目里改 `web/workbench.html` 的页签、模块、按钮名、配色，不重新设计样式。要改，先照基线交，把用户原话记进台账 U 类，等用户说“升级界面基线”。
- 不把密钥、口令写进任何文件。
- 改了页面不跑 `tests/` 就交付。
