#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q1 案例质检脚本（lsl-core-story-prompt v0.1.0，规则见 references/qa.md）。

读一份工作台档案，查能自动查的硬项和软项，其余标“人工核对”并列出要看的东西，写成 Markdown 质检报告。

输入可以是三种 JSON 之一：
  1. 工作台数据库文档 projects/<id>：{"title":..., "updatedAt":..., "json":"<整份档案的字符串>"}
  2. 整份档案本身：{"v":1, "title":..., "script":{...}, ...}
  3. 样例种子 seed.json：{"project":{...}, "checkpoints":[...]}

用法：
  python3 qa_check.py 档案.json --out 质检报告-Q1-v01.md [--genre 情感] [--link 工作台链接] [--id 项目id]
"""
import argparse, json, re, sys, datetime

BANNED = re.compile(r"(爱情|坚守|思念|家国|情怀|命运|灵魂|深情|感动)")
MOOD = re.compile(r"(悲伤|难过|痛苦|开心|幸福|激动|伤心|绝望|欣慰|感慨|动情|心碎|喜悦|哀伤|悲痛)")
RISKY = re.compile(r"(停在半空|读两遍|嘴角|眼神|眨|手指|指尖|颤|咽|呼一口气|泪)")
DENSITY = {"情感": (3, 6), "带货": (2, 4), "玄幻": (2, 4), "打斗": (2, 4), "悬疑": (3, 6), "喜剧": (2, 5), "多集": (2, 6)}
VERSION = "lsl-core-story-prompt v0.1.0 · 界面基线 CSP-UI-1"


def load_state(path):
    d = json.load(open(path, encoding="utf-8"))
    if isinstance(d, dict) and "project" in d and "json" in d.get("project", {}):
        d = d["project"]
    if isinstance(d, dict) and isinstance(d.get("json"), str):
        return json.loads(d["json"])
    return d


class Q:
    def __init__(self, S):
        self.S = S
        self.segs = ((S.get("script") or {}).get("segments")) or []
        self.D = S.get("duration") or (self.segs[-1]["b"] if self.segs else 0)

    def ep_chosen(self):
        e = self.S.get("ep") or {}
        return next((c for c in e.get("candidates", []) if c.get("id") == e.get("chosen")), None) if e.get("chosen") else None

    def ep_text(self):
        c = self.ep_chosen()
        return c["text"] if c else ""

    def seg_state(self, code):
        return (self.S.get("seg") or {}).get(code) or {}

    def seg_chosen(self, code):
        g = self.seg_state(code)
        if not g.get("chosen"):
            return None
        return next((c for c in g.get("candidates", []) if c.get("id") == g["chosen"]), None)

    def seg_stale(self, code):
        g = self.seg_state(code)
        return bool(g.get("candidates") and g.get("basedOn") and g.get("basedOn") != self.ep_text())

    def segs_hash(self):
        return "|".join(s["code"] + ":" + ((self.seg_chosen(s["code"]) or {}).get("text", "")) for s in self.segs)

    def tables_fresh(self):
        T = self.S.get("tables")
        return bool(T and T.get("basedOn") == self.segs_hash())


def test_of(c):
    miss = [k for k, f in (("人", "person"), ("东西", "object"), ("动作", "action"), ("变化", "change")) if not str(c.get(f) or "").strip()]
    return miss, bool(BANNED.search(c.get("text") or ""))


def tstr(a, b):
    return "（%s–%s）%s 秒" % (a, b, b - a)


def run(S, genre):
    q = Q(S)
    R = []  # (id, name, status, detail)  status: 过 / 不过 / 人工核对 / 未到这一步

    def add(i, name, st, det):
        R.append((i, name, st, det))

    # H1 剧本事实不改
    raw = (S.get("script") or {}).get("raw") or ""
    det, bad = [], False
    if not q.segs:
        add("H1", "剧本事实不改", "未到这一步", "还没分段")
    else:
        if q.segs[0]["a"] != 0:
            bad = True; det.append("第一段不是从 0 秒开始")
        for x, y in zip(q.segs, q.segs[1:]):
            if x["b"] != y["a"]:
                bad = True; det.append("%s 和 %s 之间秒数没接上（%s / %s）" % (x["code"], y["code"], x["b"], y["a"]))
        if q.segs[-1]["b"] != q.D:
            bad = True; det.append("最后一段停在 %s 秒，全片 %s 秒" % (q.segs[-1]["b"], q.D))
        quotes = [m for s in q.segs for m in re.findall(r"“([^”]{2,})”", s.get("text") or "")]
        missing = [m for m in quotes if raw and m not in raw]
        if missing:
            bad = True; det.append("这些引号里的原话在剧本原文里找不到：" + "；".join(missing[:8]))
        det.append("%d 段、%s 秒；引号原话 %d 处，对上 %d 处" % (len(q.segs), q.D, len(quotes), len(quotes) - len(missing)))
        det.append("人工再看：剧本写死的事件是不是都在节拍里出现")
        add("H1", "剧本事实不改", "不过" if bad else "人工核对", "；".join(det))

    # H2 集核心能拍
    ec = q.ep_chosen()
    if not ec:
        add("H2", "集核心能拍", "未到这一步", "还没选集核心")
    elif ec.get("own"):
        add("H2", "集核心能拍", "人工核对", "用的是用户自己写的：“%s”——人工对人、东西、动作、变化四项" % ec["text"])
    else:
        miss, ban = test_of(ec)
        add("H2", "集核心能拍", "不过" if (miss or ban) else "过",
            "“%s”" % ec["text"] + ("；缺：" + "、".join(miss) if miss else "") + ("；有禁用词" if ban else ""))

    # H3 段核心都能拍
    if not q.segs:
        add("H3", "段核心都能拍", "未到这一步", "还没分段")
    else:
        lines, st = [], "过"
        for s in q.segs:
            c = q.seg_chosen(s["code"])
            if not c:
                lines.append("%s 还没选" % s["code"]); st = "未到这一步" if st != "不过" else st; continue
            if q.seg_stale(s["code"]):
                lines.append("%s 待重算（按旧集核心写的）" % s["code"]); st = "不过"; continue
            if c.get("own"):
                lines.append("%s 用户自己写的，人工核对" % s["code"])
                if st == "过": st = "人工核对"
                continue
            miss, ban = test_of(c)
            if miss or ban:
                st = "不过"; lines.append("%s 缺 %s%s" % (s["code"], "、".join(miss) or "—", "，有禁用词" if ban else ""))
        n = sum(1 for s in q.segs if q.seg_chosen(s["code"]))
        add("H3", "段核心都能拍", st, "已选 %d/%d 段" % (n, len(q.segs)) + ("；" + "；".join(lines) if lines else "；四项都有、没有禁用词"))

    # H4 连读成立
    t = S.get("test")
    if not all(q.seg_chosen(s["code"]) and not q.seg_stale(s["code"]) for s in q.segs) or not q.segs:
        add("H4", "连读成立", "未到这一步", "段核心没选完")
    elif not t:
        add("H4", "连读成立", "不过", "还没做能拍测试（节点 07）")
    elif t.get("basedOn") != q.segs_hash():
        add("H4", "连读成立", "不过", "能拍测试是按旧的段核心做的，要重测")
    else:
        iss = t.get("issues") or []
        add("H4", "连读成立", "过" if (t.get("ok") and not iss) else "人工核对",
            (t.get("summary") or "") + ("；提出 %d 处：" % len(iss) + "；".join("%s %s" % (x.get("code", ""), x.get("problem", "")) for x in iss) + "——人工确认每处都处理了" if iss else ""))

    T = S.get("tables") if q.tables_fresh() else None
    if not T:
        why = "四张表还没写" if not S.get("tables") else "四张表是按旧的段核心写的，要重写"
        for i, n in (("H5", "秒数盖满"), ("H6", "每拍推进核心"), ("H7", "物件有去向"), ("H9", "提案都取舍过")):
            add(i, n, "未到这一步", why)
    else:
        beats = sorted(T.get("beats") or [], key=lambda b: b["a"])
        gaps = []
        if not beats:
            gaps.append("节拍表是空的")
        else:
            if beats[0]["a"] != 0: gaps.append("第一拍从 %s 秒开始" % beats[0]["a"])
            for x, y in zip(beats, beats[1:]):
                if x["b"] != y["a"]: gaps.append("%s 秒和 %s 秒之间%s" % (x["b"], y["a"], "空了" if y["a"] > x["b"] else "重叠"))
            if beats[-1]["b"] != q.D: gaps.append("最后一拍停在 %s 秒，全片 %s 秒" % (beats[-1]["b"], q.D))
        add("H5", "秒数盖满", "不过" if gaps else "过", "；".join(gaps) if gaps else "%d 拍，0 到 %s 秒首尾相接" % (len(beats), q.D))
        empty = [tstr(b["a"], b["b"]) for b in beats if not str(b.get("core") or "").strip()]
        add("H6", "每拍推进核心", "不过" if empty else "过", ("“核心走到哪”空着：" + "、".join(empty)) if empty else "每拍都写了")
        noend = [p.get("name", "?") for p in (T.get("props") or []) if not str(p.get("end") or "").strip() or re.search(r"[？?]|未|不明", str(p.get("end")))]
        add("H7", "物件有去向", "不过" if noend else "过", ("没交代最后去哪：" + "、".join(noend)) if noend else "%d 样都交代了" % len(T.get("props") or []))
        dec = S.get("decisions") or {}
        left = [p.get("text", "") for p in (T.get("proposals") or []) if not dec.get(p.get("id"))]
        add("H9", "提案都取舍过", "不过" if left else "过", ("还没取舍：" + "；".join(left)) if left else "%d 条都取舍了" % len(T.get("proposals") or []))

    # H8 标注落实（人工）
    annos = []
    for a in ((S.get("ep") or {}).get("annotations") or []):
        annos.append("集核心 · 候选 %s“%s”→ %s" % (a.get("cand"), a.get("quote", ""), a.get("note")))
    for s in q.segs:
        for a in (q.seg_state(s["code"]).get("annotations") or []):
            ch = q.seg_chosen(s["code"])
            annos.append("%s · 候选 %s“%s”→ %s（现在选的是 %s）" % (s["code"], a.get("cand"), a.get("quote", ""), a.get("note"), (ch or {}).get("id", "未选")))
    add("H8", "标注落实", "人工核对" if annos else "过", ("逐条确认在最终核心或四张表里有对应改动：" + "；".join(annos)) if annos else "没有标注")

    # H10 版权（半自动）
    subs = [s["code"] + "：" + m for s in q.segs for m in re.findall(r"字幕[：:]?\s*(?:“[^”]*”|（[^）]*）|[^。；]*)", s.get("text") or "")]
    lyr = [x for x in subs if "（剧本字幕）" not in x and "“" not in x]
    add("H10", "版权", "人工核对",
        "字幕 %d 处，其中写成“（剧本字幕）”的 %d 处；逐条确认没有复述歌词：%s" % (len(subs), sum("（剧本字幕）" in x for x in subs), "；".join(subs[:12])) + ("；这些字幕写法要看：" + "；".join(lyr) if lyr else ""))

    # 软项
    if T:
        beats = T.get("beats") or []
        moody = [tstr(b["a"], b["b"]) for b in beats if BANNED.search(b.get("acting") or "") or MOOD.search(b.get("acting") or "")]
        ratio = 1 - (len(moody) / len(beats)) if beats else 0
        add("S1", "具体度", "过" if ratio >= 0.8 else "不过", "动作拍占 %.0f%%" % (ratio * 100) + ("；写了情绪词的拍：" + "、".join(moody) if moody else ""))
        noro = [x.get("name", "?") for x in (T.get("scenes") or []) if not str(x.get("role") or "").strip()]
        add("S2", "场景有用", "不过" if noro else "过", ("说不出在核心里干什么：" + "、".join(noro)) if noro else "%d 个场景都写了" % len(T.get("scenes") or []))
        rules = [r for r in (T.get("rules") or []) if re.search(r"只|不", r)]
        add("S3", "收放有规矩", "人工核对" if rules else "不过", ("管收放的规矩：" + "；".join(rules) + "——人工看节拍里有没有破") if rules else "全片规矩里没有管收放的一条")
        lo, hi = next((v for k, v in DENSITY.items() if k in (genre or "")), (2, 8))
        ok = [b for b in beats if lo <= (b["b"] - b["a"]) <= hi]
        r2 = len(ok) / len(beats) if beats else 0
        add("S4", "节拍密度", "过" if r2 >= 0.8 else "不过", "类型“%s”参考每拍 %s—%s 秒；%d/%d 拍在范围内" % (genre or "未写", lo, hi, len(ok), len(beats)))
        risky = [tstr(b["a"], b["b"]) + " " + (b.get("acting") or "")[:24] for b in beats if RISKY.search(b.get("acting") or "")]
        add("S5", "AI 风险", "人工核对", ("可能拍不稳、要备简化写法的拍：" + "；".join(risky[:10])) if risky else "没找到常见的高风险动作")
    else:
        for i, n in (("S1", "具体度"), ("S2", "场景有用"), ("S3", "收放有规矩"), ("S4", "节拍密度"), ("S5", "AI 风险")):
            add(i, n, "未到这一步", "四张表还没写或要重写")
    add("S6", "人的打分", "人工核对", "请用户看完四张表打 1—5 分：像不像要的戏（≥4 分合格）")
    return q, R


def report(S, q, R, args):
    hard = sorted([r for r in R if r[0].startswith("H")], key=lambda r: int(r[0][1:]))
    passed = all(r[2] == "过" for r in hard)
    pending = [r[0] for r in hard if r[2] == "未到这一步"]
    failed = [r[0] for r in hard if r[2] == "不过"]
    manual = [r[0] for r in hard if r[2] == "人工核对"]
    if passed:
        verdict = "放行：10 条硬项全过"
    elif failed:
        verdict = "不放行：硬项不过 " + "、".join(failed) + ("；还没到 " + "、".join(pending) if pending else "")
    elif pending:
        verdict = "进行中：还没到 " + "、".join(pending) + ("；待人工核对 " + "、".join(manual) if manual else "")
    else:
        verdict = "待人工核对：" + "、".join(manual) + "（核对都过才放行）"
    L = ["# 质检报告 · Q1 · %s" % (S.get("title") or ""), "",
         "- **结论**：%s" % verdict,
         "- **版本**：%s" % VERSION,
         "- **档案**：%s%s" % (args.link or "（工作台链接）", (" · 项目 " + args.id) if args.id else ""),
         "- **时间**：%s（脚本自动部分；人工核对的结论由 Claude 补在下面）" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
         "- **类型**：%s；%d 段，%s 秒" % (args.genre or "未写", len(q.segs), q.D), "",
         "## 硬项（全过才能交给导演 skill）", "", "| 编号 | 项 | 结果 | 说明 |", "|---|---|---|---|"]
    for r in hard:
        L.append("| %s | %s | %s | %s |" % (r[0], r[1], r[2], r[3].replace("|", "／")))
    L += ["", "## 软项（不过不拦，记进方法论台账）", "", "| 编号 | 项 | 结果 | 说明 |", "|---|---|---|---|"]
    for r in R:
        if r[0].startswith("S"):
            L.append("| %s | %s | %s | %s |" % (r[0], r[1], r[2], r[3].replace("|", "／")))
    L += ["", "## 人工核对结论", "", "（Claude 逐条补：H1、H8、H10、S3、S5、S6，以及脚本标“人工核对”的其他项。）", "",
          "## 发现的问题怎么归类", "", "| 问题 | 剧本 / 操作 / 方法 | 怎么改 | 进台账编号 |", "|---|---|---|---|", "|  |  |  |  |", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="lsl-core-story-prompt Q1 案例质检")
    ap.add_argument("input")
    ap.add_argument("--out")
    ap.add_argument("--genre", default="")
    ap.add_argument("--link", default="")
    ap.add_argument("--id", default="")
    args = ap.parse_args()
    S = load_state(args.input)
    q, R = run(S, args.genre)
    md = report(S, q, R, args)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(md)
    else:
        sys.stdout.write(md)
    print("\n" + md.splitlines()[2], file=sys.stderr)


if __name__ == "__main__":
    main()
