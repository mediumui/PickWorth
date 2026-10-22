# PickWorth GEO 审计诊断（生成式引擎优化）

- 站点：https://pickworth.top（AI 工具评测独立站，Cloudflare Pages 零构建，全站 28 个索引页）
- 审计日期：2026-10-22
- 审计对象：20 篇内容页（tools 5 / comparisons 5 / lists 5 / blog 5）+ 7 个手写页 + 404
- 结论一句话：**结构化数据与 OG/Twitter 卡片已到位（上轮 SEO 完成），但 GEO（被 AI 答案引擎"看到并被引用"）的核心信号几乎全部缺失——最致命的是"权威外部引用"与"FAQ/QA 结构"两条主线，整站 0 页触发。**

---

**范围**：英文 AI 工具测评站，Cloudflare Pages 零构建。

## 一、缺口清单（按优先级）

### P0 — 决定性缺口（直接决定"是否被 AI 召回/采信"）

| # | 缺口 | 证据 | 影响 | 状态 |
|---|------|------|------|------|
| P0-1 | **整站 0 条外部权威引用链接** | 28 页 0 条外部 `<a href>` | GEO 第 1 大引用信号缺失 | **已修复**：18 页 47 条外部链接 |
| P0-2 | **草稿已有真实 URL 但渲染器从未输出** | `{{SOURCES}}` 组件未引入模板 | 现有资产埋着不用 | **已修复**：4 模板全部接入 `{{SOURCES}}` |
| P0-3 | **`sources` 字段 64 条为脏格式** | 7 篇旧稿 `["#anchor","Label"]` 数组 | 放出会渲染成脏数据 | **已修复**：`tools/clean_sources.py` + `tools/fix_cursor_sources.py` 清洗为 `text — url` 字符串 |
| P0-4 | **整站 0 页 FAQPage / QAPage schema** | 28 页 faqpage 命中 0 | 第 6 大信号缺失 | **已修复**：20 页全部带 `FAQPage` schema |
| P0-5 | **无 `llms.txt` / `llms-full.txt`** | 站点根目录不存在 | 第 9 大信号缺失 | **已修复**：`tools/gen_llms_txt.py` 生成 |

### P1 — 高价值优化（显著提升被引用率）

| # | 缺口 | 说明 | 状态 |
|---|------|------|------|
| P1-1 | **内容缺"可直接成句的独立结论块"** | 每页顶部加 `<dl class="key-answers">` | **已修复**：20 页全部带 `key-answers` 区块（answer + 5-9 个 QA 对） |
| P1-2 | **缺实体定义前置（"X 是什么"一句话）** | 用 `answer` 字段渲染为 `p.key-answer` | **已修复**：20 页全部带 |
| P1-3 | **对比页缺"判定性结论句"** | 同上，对比页 `answer` 给出"谁在 X 场景赢、因为 Y" | **已修复** |
| P1-4 | **数字信号密度低** | 保证每页 ≥3 个具体数字 | 部分改善：`llms-full.txt` 自动抽 "Key numbers" 块；正文数字密度需后续补 |
| P1-5 | **品牌实体未集中到"事实枢纽"** | 已在 `Organization` schema + `llms.txt` 摘要里暴露实体事实 | 部分改善：事实枢纽需后续建 `/about/entity-hub` 页 |
| P1-6 | **缺 query-intent 同义词（search-terms）** | 加 `<meta name="search-terms">` 让 AI 检索层能映射不同问法 | **已修复**：20 页全部带 `search_terms`（每页 4-14 个同义短语） |

### P2 — 长期/监测

| # | 缺口 | 说明 | 状态 |
|---|------|------|------|
| P2-1 | **无 AI 答案引用监测** | 手动探针表 + KPI CSV | **已交付**：`tools/citation_probe.md` + `tools/citation_monitor.csv` |
| P2-2 | **未做 RAG 召回预估** | 词汇 BM25 代理 | **已交付**：`tools/rag_recall.py` + `tools/probe_queries.txt` + `tools/rag_recall_report.md`（12 条查询 top-2 命中 3/12，已暴露真实缺口） |
| P2-3 | **竞品声量未监测** | 暂未做 | 后续 |

## 二、本轮落地清单

1. `llms.txt`（42 行）+ `llms-full.txt`（140 行）：站点根目录，Cloudflare 直接托管，`tools/gen_llms_txt.py` 可再生成
2. `tools/clean_sources.py` + `tools/fix_cursor_sources.py`：清洗 8 篇旧稿的脏 `sources`
3. `tools/l4_render.py` 升级：`_sources_list` 接受 em-dash/hyphen 双分隔；新增 `{{KEY_ANSWERS}}`/`{{FAQ_LD}}`/`{{SEARCH_TERMS}}` 占位
4. `src/templates/{reviews,compare,lists,blog}/*-template.html`：全部接入 `{{SOURCES}}` + `{{KEY_ANSWERS}}` + `{{FAQ_LD}}` + `{{SEARCH_TERMS}}`
5. `src/components/_sources.html`：`{{SOURCES_LIST}}` 从注释里放出（原来被 `_strip_comments` 吞掉，导致 `<ol>` 一直空）
6. `assets/css/site.css`：`.key-answers` / `.key-answer` / `.qa-list` / `.qa` 样式
7. 20 篇 `content/drafts/*.json`：新增 `answer`（一句话可引用结论）+ `key_answers`（5-9 个 QA 对）+ `search_terms`（4-14 个同义短语）
8. 监测工具：`tools/citation_probe.md`（12 条查询手动探针表）+ `tools/citation_monitor.csv`（KPI 监测 CSV 模板）+ `tools/rag_recall.py` + `tools/rag_recall_report.md`

## 三、已验证

- `tools/l4_render.py --all`：20 篇渲染，0 失败
- `tools/sync_chrome.py --check`：0 漂移，28 页全一致
- `tools/verify_refs.py`：28 页 0 断链
- JSON-LD 全量：全站 100 块，逐块 `json.loads` 全合法，0 非法
- 外部引用链接：18 页 / 47 条（从 0 起步）
- FAQPage schema：20/20 内容页
- key-answers 区块：20/20 内容页
- search-terms meta：20/20 内容页
- meta description：0 条 >160 字符
- `llms.txt` / `llms-full.txt`：根目录就位，可直接被 Cloudflare Pages 托管

## 四、下一步（P1-4/P1-5/P2-3）

1. **数字密度**：评测/对比页正文每页补 3-5 个具体数字（价格、速度倍数、词数、上下文 GB），目前只有 verdict 段有
2. **事实枢纽**：`/about/entity-hub/` 新页，把"PickWorth 是什么、谁写、评分体系、更新频率"做成一个可被引用的事实清单 + JSON-LD
3. **AI-SOV 监测**：在 `citation_monitor.csv` 里加 2-3 个竞品（如 The Verge / TechCrunch / 某 AI 评测站）的行，每月跑一遍看声量份额

> 高合规行业：本站属通用评测（金融/医疗/教育均不涉），无需走 `compliance_guardrails.md` 金融医疗专项。
