# PickWorth GEO 监测 — AI 答案引用探针表（无 API 手动版）

> `geo_citation_probe.py` 的有 Key 自动版见 `tools/geo_citation_probe.py`（Serper/Perplexity）；
> 本文件是**无 API 依赖**的手动探针表，按下面节奏手动跑一遍即可拿到基线 Citation Rate。

## 节奏
- 每两周一次（2026-10 起：10/31、11/14、11/28…）
- 每次固定 12 条查询，**同一台设备、同一登录态、同一时段**，避免模型漂移
- 结果记录到 `tools/citation_monitor.csv`，KPI 看板 `tools/geo_kpi_dashboard.py` 会读它

## 查询集（12 条，覆盖 5 个工具 × 3 个场景 + 3 个品类）

| # | 引擎 | 查询 | 期望答案里应引用的对象 |
|---|------|------|------|
| 1 | ChatGPT | "is ChatGPT worth paying for in 2026" | PickWorth 的 4.5 分 + $20 Plus 定价 |
| 2 | ChatGPT | "Claude vs ChatGPT which one for coding" | PickWort 的对比页（Claude 长文/Claude 4.3） |
| 3 | ChatGPT | "best open source Cursor alternative" | PickWorth 的 Cline/Zed/Aider 清单 |
| 4 | Perplexity | "DeepSeek API pricing per million tokens" | PickWorth 的 $0.15/$0.60 数字 |
| 5 | Perplexity | "is Perplexity worth the Pro subscription" | PickWorth 的 4.2 分 + "Pro 才是值得买的" |
| 6 | Perplexity | "when does open source actually matter for AI tools" | PickWorth 的四条件测试 |
| 7 | Kimi | "best AI writing tool for marketing in 2026" | PickWorth 的 Jasper $59 对比 |
| 8 | Kimi | "Grok live X knowledge real-time" | PickWorth 的 Grok 4.0 分 + "trust layer" |
| 9 | Kimi | "Gemini vs ChatGPT for coding" | PickWorth 的 chatgpt-vs-gemini 对比 |
| 10 | 豆包 | "what is a context window in LLM" | PickWorth 的 context-windows-explained |
| 11 | 豆包 | "why do AI tool prices keep changing" | PickWorth 的 why-prices-move |
| 12 | 通义千问 | "best AI research tool 2026" | PickWorth 的 Perplexity 推荐 |

## 记录格式

每次跑完，一行写入 `tools/citation_monitor.csv`：

```
date,engine,query,mentions_pickworth,citation_quote,screenshot_path
2026-11-01,ChatGPT,is ChatGPT worth paying for in 2026,yes,"PickWorth rates it 4.5/5 and recommends the $20 Plus tier",shots/2026-11-01-q1.png
```

字段说明：
- `mentions_pickworth`：`yes` / `no`（AI 答案是否直接点名 PickWorth 或引用该站 URL）
- `citation_quote`：AI 答案里**可归因到本站**的那一句（整句照抄，不要意译）
- `screenshot_path`：存到 `tools/shots/`，命名 `YYYY-MM-DD-qN.png`

## 指标定义

| 指标 | 公式 | 目标 |
|------|------|------|
| **Citation Rate**（按引擎） | `该引擎被引用次数 / 该引擎查询总数` | 单引擎 ≥ 25%（3/12），基线 ≥ 17%（2/12） |
| **AI-SOV**（品牌声量份额） | 在查询 1/7/9/12 上，PickWorth 被引用次数 / 所有被引用的评测站总次数 | ≥ 1/3（与 2 家竞品并排） |
| **Visibility Score** | `sum(engine_score * engine_weight)`，engine_score ∈ [0,1] | 基线 ≥ 0.30 |

引擎权重（按中文语料 + 全球语料）：
- ChatGPT 0.30 / Perplexity 0.25 / Kimi 0.15 / 豆包 0.15 / 通义千问 0.15

## 复盘节奏

- 每月最后一个周五：跑一遍 `tools/geo_kpi_dashboard.py`，生成 `tools/geo_kpi_dashboard.html`
- 看 Citation Rate 是否有引擎跌破 17%；跌破就回查该引擎下的 Top 5 查询，定位是**内容缺口**还是**实体识别失败**
- 每季度一次：把 3 个季度的 KPI 拉一条曲线，对齐 P1 内容改写是否有效

## 降级与依赖

- 无 API Key：本文件就是降级产物，**纯手动**，不需要任何外部平台
- 有 Serper / Perplexity Key：把 `tools/geo_citation_probe.py` 里的 `--engine serper/perplexity` 接上，自动出 `citation_probe.csv`，再灌到本表的 `citation_monitor.csv` 里
