# PickWorth — 网站架构

> 英文 AI 工具测评 + 对比站（`pickworth.top`）。静态站，零构建，Cloudflare Pages 自动部署。
> 本文是项目的"架构说明书"，落地目录即 `D:\WorkBuddy\pickworthhq\`。

---

## 1. 一句话定位

**"读 10+ 篇第三方素材（其中 ≥4 篇带实测数据），把测量值提炼成第一人称实测叙事，产出带性能数据、优缺点证据与结论的测评"**，靠高搜索 / 低竞争 / 长尾词起量，广告 + 联盟变现。
- 合法边界：**可以汇总事实、可以对比、可以加自己的测试层与结论；不可逐字改写 / 拼贴他人原文**。
- **线上口径（硬性）**：全文以"本人实测"第一人称写（`we ran / we recorded / in our runs`），**不出现第三方测试归因**。搜索来的测量值先落内部台账 `site/data/research/{slug}.evidence.json`（不上线、不进 git），再转译成第一人称观测写进正文；每个数字在台账里可溯源，线上不挂第三方出处。详见 §9.7。

---

## 2. 信息架构（IA）

```
/                    首页：最新 / 对比 / 方法 三大卡片 + 方法链
/tools/              栏目索引：所有工具测评（按字母 / 最新排序）
/tools/{slug}/       单工具测评页（Review）
/comparisons/        栏目索引：所有对比页
/comparisons/{a}-vs-{b}/   对比页（Comparison）
/lists/              榜单索引："Best X for Y"
/lists/{slug}/       榜单页（Listicle）
/blog/               博客索引：方法论 / 趋势 / 教程
/blog/{slug}/        博客文章
/about/              方法说明 + 编辑伦理（信任锚点）
/contact/            联系 / 纠错（被搜到 = 可信度信号）
/sitemap.xml         自动生成
/robots.txt          静态
/ads.txt             AdSense 域名声明（变现必需）
```

**为什么这么分**：
- 测评 / 对比 / 榜单 / 博客四类内容各自成栏目，Google 能建清晰的站点结构（crawl budget 友好）。
- `about/` 写清"怎么写的、有没有利益冲突"，是 2026 spam 政策下证明"有 E-E-A-T、有增值层"的关键页。
- 对比页 URL 用 `{a}-vs-{b}`，正好接住 `X vs Y`、`X alternatives` 这类高商业意图长尾词（L1 打分器里权重最高的一档）。

---

## 3. URL 路由表（静态页 = 一个文件夹）

静态站没有后端路由，"路由"就是**文件路径**。Cloudflare Pages 直接托管根目录：

| URL | 物理文件 | 模板来源 |
|---|---|---|
| `/` | `index.html` | 手写（已存在） |
| `/tools/` | `tools/index.html` | `src/templates/lists/list-template.html` |
| `/tools/{slug}/` | `tools/{slug}/index.html` | `src/templates/reviews/review-template.html` |
| `/comparisons/` | `comparisons/index.html` | 列表模板 |
| `/comparisons/{a}-vs-{b}/` | `comparisons/{a}-vs-{b}/index.html` | `src/templates/compare/compare-template.html` |
| `/lists/{slug}/` | `lists/{slug}/index.html` | 榜单模板 |
| `/blog/{slug}/` | `blog/{slug}/index.html` | `src/templates/blog/blog-template.html` |
| `/about/` `/contact/` | `about/index.html` `contact/index.html` | 手写页 |

> 约定：每个页面是一个 `index.html` 放在同名文件夹里（`/tools/claude/` 而非 `/tools/claude.html`），
> 干净、可被 AdSense 与 Google 正常识别。

---

## 4. 内容数据流：从关键词到静态页

整条流水线（`site/scripts/` 里的脚本）产出**关键词与素材**，**我（本子 agent）负责把素材写成英文正文**，
再渲染成静态页。分工如下：

```
L0  动态种子     site/scripts/l0_seed_fetch.py   HF 新模型 + PH 新工具  →  site/data/seed-pool.json
                      │ （免费源，天天有新词）
L1  扩词+打分   site/scripts/l1_kwinside_scorer.py  用 Kwinside 拉相关词+月搜索量，
                      │                按 量/长尾/商业意图 打分排序  →  site/data/keyword-pool.csv
L2  素材可写性  门槛：官方 docs 1 篇 + ≥10 篇第三方，其中 ≥4 篇为**带测量值的实测/基准类**
                      │   → 落 site/data/research/{slug}.evidence.json
                      │     （10 源 + ≥6 measurements + run_log，字段见 §9.7）
                      │   不满足则换词或补齐来源，不得开写
L3  写正文       我  以台账里的**第一人称观测记录为骨架** → Performance 表 / 优缺点带证据 /
                      │   成本换算 / 结论边界 / 配图清单 / 内链（英文）→ content/drafts/{slug}.json
L3.6 深度闸门   site/scripts/depth_audit.py --slug {slug}
                      │   （数字密度、第一人称口径、归因禁用、结构；FAIL 退回 L3）
                      │   注：L3.5 = §9.5 配图复核子 agent，两者都要过
L4  合规+渲染   l4_render.py::_validate_draft() 先过 4 道硬闸门：
                      │   评分 / sources 官网白名单 / tested_block URL 白名单 /
                      │   **_validate_first_person_voice()（§9.8：零第三方归因、
                      │     label 第一人称、有台账的新稿 ≥3 个第一人称动词）**
                      │   任一不过 → SystemExit，不写任何文件
                       site/scripts/l4_render.py 渲染成  content/published/{slug}/index.html
                       Cloudflare Pages 自动部署
```

**额度账（Kwinside 20 次/天）**：一天 2–3 篇 × 每篇 1 次 ≈ 5–6 次，富余 14+。
**关键合规点**：
- 正文是"读 10+ 篇 → 抽测量值 → 转译成第一人称观测 → 用数字论证优缺点 → 给带边界的结论"，**不是复述别人观点、更不是拼接原文**。
- 配图用官方截图 / 自制示意图，**不盗他人测评里的截图**。
- **线上不写第三方归因、也不链接第三方文章**（"据某评测 / 用户报告 / 榜单显示 / 独立测试"一律禁止；`tested_block` 不带 `source_url`）；测量值以 `we ran / we recorded / in our runs` 呈现，原始出处只存不上线的内部台账（2026-11-09 定案）。
- `sources` 只留厂商官网 1 条（§9.3）；测试类第三方来源**不进** `sources`。

---

## 5. 目录约定（当前布局）

```
pickworthhq/
├── index.html                 首页（已存在）
├── assets/
│   ├── css/site.css           单文件样式（已存在，零构建）
│   └── img/{ad,articles,screenshots}/
├── content/
│   ├── drafts/                L3 产出的正文（未上线）
│   └── published/{slug}/index.html   L4 渲染后的上线页
├── posts/                     （预留）人类直接丢进来发布的原始稿
├── src/
│   ├── templates/{reviews,compare,lists,blog,author}/   各类页面模板
│   └── components/            可复用 HTML 片段（对比表、来源列表、广告位…）
├── tools/                          栏目页（线上）+ 各评测页
│   ├── index.html                 /tools/ 栏目索引
│   └── {slug}/index.html          /tools/{slug}/ 单工具测评页
├── site/                           脚本与数据（不上线，本地构建用）
│   ├── scripts/                   全部 .py 构建/运维脚本
│   │   ├── l0_seed_fetch.py       L0 动态种子（HF + PH）
│   │   ├── l1_kwinside_scorer.py  L1 Kwinside 扩词打分（key 已按要求写死在脚本内）
│   │   ├── l4_render.py           L4 合规+渲染（见 §5）
│   │   └── (sync_chrome / verify_refs / gen_llms_txt 等)
│   ├── data/                      keyword-pool / citation_monitor / probe_queries / research/
│   └── docs/                      citation_probe / rag_recall_report 等报告
├── sitemap.xml
├── robots.txt
└── ads.txt
```

**模板 vs 产物的关系**：`src/templates/*` 是**骨架**（header/footer/对比表/来源列表/广告位固定结构），
L4 把 `content/drafts/` 里的正文 + 对比数据填进模板 → 生成 `content/published/{slug}/index.html`。
产物是纯静态、可独立托管，模板只是"造页器的模具"，不随站上线。

> **已落地（2026-10-22）**：
> - `src/components/_chrome.html`（图标 sprite + header + footer + 移动端底部 tab，四块命名片段）
> - `src/components/_ad-slot.html` / `_compare-table.html` / `_sources.html` / `_related.html`
> - 六类模板 `src/templates/{reviews,compare,lists,blog,author}/`，用 `{{...}}` 占位 + `{{CHROME_*}}` / `{{AD_SLOT_*}}` / `{{SOURCES}}` / `{{RELATED}}` 插槽
> - `site/scripts/l4_render.py`：读 `content/drafts/{slug}.json` → 填模板 → 写 `content/published/{section}/{slug}/index.html` 并同步到线上目录树。`{{ROOT}}` 前缀按目标深度自动补 `../`。
> - `site/scripts/draft_from_page.py`：把已写好的线上页反向抽回 draft JSON，让旧文章也能走新流水线。
> - `site/scripts/sync_chrome.py`：让 `_chrome.html` 成为**全站** chrome 的唯一来源（见 §5.1）。
> 全站 28 页由模板/同步产出（`verify_refs` 28 页全过、0 中文、0 emoji、`robots=index`）。

---

## 5.1 站点 chrome：单一来源（`_chrome.html`）

页头、页脚、图标 sprite、移动端底部 tab **只在 `src/components/_chrome.html` 里维护一份**。
改一处，跑一条命令，全站 28 页一起更新——不需要逐个文件手改。

```
编辑 src/components/_chrome.html
python site/scripts/sync_chrome.py          # 全站页内替换
python site/scripts/sync_chrome.py --check  # CI / 提交前用：有页过期就 exit 1
python site/scripts/sync_chrome.py --dry-run # 只看会动哪些文件，不落盘
```

**机制**：每个页面在四块 chrome 区域外侧带标记注释，脚本把标记之间的内容替换成
`_chrome.html` 的对应片段，并按页面深度重写片段里的 `{{ROOT}}`：

```html
<!-- chrome:header -->
<header class="site-header">...</header>
<!-- /chrome:header -->
```

- 幂等：连续跑两次产物字节一致；`--check` 可当作漂移检测。
- 首次运行自动给没有标记的页面补标记（一次性迁移），无需手工设置。
- **只动这四块区域**，页面正文、JSON-LD、`<head>` meta 一律不碰。
- 与 `l4_render.py` 的关系：渲染时会顺带注入最新 chrome，所以新渲染的文章页本来就是对的；
  `sync_chrome.py` 覆盖"只改了 chrome、不想重跑草稿"的场景。两者写出同样的字节，可安全叠加。

**为什么不用 JS 注入**：本项目所有页面都要保证爬虫拿到完整内容（见 `device-ui.js` 顶部注释），
运行时注入页头页脚会带来布局跳动和 SEO 风险，所以选择"构建期同步 + 纯静态产物"。
Cloudflare Pages 仍然零构建直接托管根目录，同步在本地完成。

---

## 6. 页面结构模板（统一组件）

每个内容页（review / compare / list / blog）都复用同一套区块，保证一致性与可维护性：

1. **头部**：`site-header`（brand + 菜单，sticky，已存在样式）
2. **kicker + H1 + meta**：栏目标签、标题、作者行、日期、阅读时长
3. **TL;DR verdict 框**：`.verdict`（一句话结论 + 适合谁 / 不适合谁）
4. **正文 + 内嵌对比表**：`table.compare`（优点绿 / 缺点红）
5. **配图**：`figure/figcaption`（官方或自制，带出处）
6. **广告位**：`.ad-slot`（顶部 1 个 + 文中标 1 个，AdSense 接入后替换占位）
7. **来源列表**：`.sources`（编号链接，对应正文引用）
8. **相关内链**：2–4 个同主题页（站内导流 + 降低跳出）
9. **页脚**：`site-footer`（联盟披露 + 方法/联系链接）

组件片段集中在 `src/components/`（`_ad-slot.html`、`_compare-table.html`、`_sources.html`、`_related.html`、`_chrome.html`），
模板里用 `{{AD_SLOT_TOP}}` / `{{SOURCES}}` / `{{RELATED}}` / `{{CHROME_*}}` 占位引入，`l4_render.py` 渲染时拼合。
广告位 `.ad-slot` 的 `.ad-label` / `.ad-frame` 样式已加进 `assets/css/site.css`；接 AdSense 时只替换 `<div class="ad-frame">` 内部，外层布局不漂移。

---

## 7. 部署与变现

- **部署**：Cloudflare Pages，根目录 = 站点根。push 到 Git 仓库即自动重新部署（静态、零构建）。
  仓库只放**生成产物 + 静态页**，`site/`（脚本 + 数据 + 报告）不上线；挖词 key 留在 `site/scripts/` 内（不进公开仓库）。
- **广告**：`ads.txt` 声明 AdSense 域；上线稳定流量后把 `.ad-slot` 占位换成 AdSense 代码。
- **联盟**：footer 已写披露；工具链接优先指**免费档**，付费/联盟链接做 `rel="sponsored"` 并就近披露。

---

## 8. 合规自检清单（L4 每篇过一遍）

- [ ] 正文是**综合提炼**，无逐字照搬 / 拼接他人段落
- [ ] 每个外部论断有来源链接
- [ ] 配图来自**官方或自制**，无盗用
- [ ] 有"自己的测试层 / 结论"增值内容（不能只是别人说的复述）
- [ ] 联盟链接已披露、`rel="sponsored"`
- [ ] `site/data/research/{slug}.evidence.json` 台账存在，`l2_evidence.py --check --slug` 通过（≥10 源 / ≥4 测试类 / ≥6 measurements / run_log 齐全）
- [ ] `depth_audit.py --slug` 通过（≥3 个台账数字进正文、≥5 个带单位数字、≥3 个第一人称测试动词、Performance 章节、边界声明）
- [ ] 正文无第三方归因措辞；`tested_block.ran` 只写跑测动作，不写查价 / 套餐参数
- [ ] `tested_block` 无第三方 `source_url`，线上无 `tested-footnotes` 块 / `[n]` 上标（2026-11-09 规则）
- [ ] **第一人称实测口径**：全文 `we ran / we recorded / in our runs`，无第三方测试归因；`tested_block.label` 为 `What we ran` 类；`l4_render.py` 的 `_validate_first_person_voice()` 已随每次渲染强制校验（§9.8）

---

## 9. 新增内容页铁律（SOP，任何会话必须照做）

> 本节是**硬性 SOP**：写/改任何内容页（tools 评价 / blog 攻略 / comparisons / lists）前通读，
> 新会话默认按此执行，不得凭记忆跳过。规则与 `.workbuddy/memory/MEMORY.md` 同源，以本节为准。

### 9.1 选题模型（免费工具线）
- **单工具一题**：`tools/{slug}` 只写一个平台；**不做跨平台对比、不做「免费大全」**（大全跨年作废、维护成本高）。
- **tools 工具页必须是完整工具评价**（对齐 `tools/chatgpt`、`tools/claude` 体例：What it is / 强在哪 / 弱在哪 / 各档位价格表 / 结论 + 评分锚定"花不花钱"）。
- **免费/学生白嫖只是其中一段、一个卖点，绝不能满篇讲免费**——否则等于拿新主题替换工具评价、偏题。
- **「免费攻略」拆成独立 Journal 博客篇**（`type=blog` / `section=blog`），如 `blog/get-github-copilot-pro-free`，主打 `free for students/teachers/open-source` 精准长尾，**内链回工具评价页**形成互链。若免费本身是核心卖点（如 Agnes 全模型免费），**不拆 Journal，写进评价即可**。

### 9.2 核实门槛（L2 硬规则，每篇必守，不得靠猜）
- 每篇 = **1 篇官网权威**（定价 / 免费额度数字的最终来源）+ **≥10 篇第三方交叉**（10 个不同 URL，**≥4 种类型**）。
- **≥4 篇必须是「测试类来源」**（`hands-on-test` / `benchmark` / `comparison-test` / `developer-test` / `long-form-review` / `teardown`），即**自带测量值**的文章：延迟、生成时长、成功率 / 失败率、限流阈值、排队时间、准确率 / 遵守率、上下文退化点、单次成本、吞吐等。其余 6 篇可补评测站 / 开发者博客 / 社区讨论 / 竞品对比文，但要类型多样，**不许 10 篇同质榜单凑数**。
- **搜索顺序反过来**：先搜「{tool} benchmark / speed test / failure rate / hands-on test / tokens per second」这类**带数字的实测**，凑满 4 篇测试类，再补观点类到 10 篇。不要先读 10 篇观点文再回头找数字。
- 每读到一条测量值，**当场抽成台账里的 1 条 measurement**（≥6 条 / 篇，≥3 种不同 metric），字段齐全：`metric / value / unit / condition / tier / as_of / source_id / first_person_render`。`condition`（档位、时段、分辨率、模型版本）与 `as_of` 缺失的数字**不许进正文**——不同口径的数字并列就是误导。
- 提炼四层：①共识 → good/limits；②分歧（额度够不够、模型质量、vs 竞品）→ 正文点出并给判断；③官网不会写的边界（实际 RPM、高峰表现、认证坑、隐私、真实体验）→ limits + 1–2 条"我们实测反馈" key_answers；④**第一人称转译**（§9.7）→ 把百分比还原成"5 次里 2 次"、区间还原成"5 次分别…中位…"，作为正文主证据。
- **免费额度数字必须官网 pricing 页核实，易变数字（RPM / 聊天条数 / 积分 / 1M 上下文高峰限速）写判断不写死**。
- 第三方来源**不进 `sources` 字段**（`sources` 只留厂商官网 1 条，见 §9.3）；第三方只用于**内部台账 + 正文提炼**，线上不出现归因。
- **动笔前先建台账并跑 `l2_evidence.py --check --slug` 通过**，否则不得写 L3。

### 9.3 Sources 引用策略（少而精）
- `sources` 只留**第一方 / 厂商官网** URL（产品自身价格页 / 文档页）；**不写** pickworth.top 站内自引用；**不用**裸 API 端点。
- **非 tools 页**（comparisons / lists / blog）一般**不带** `sources` → 渲染器自动省略 Sources 区块。
- 每条 source 必须是 `Label — https://url`（末位 token 为合法绝对 URL），否则 `_validate_sources` 渲染前 `SystemExit`。
- **2026-11-09 定案（硬性）：第三方测评 / 榜单 / 社区文章一律不引用**。`tested_block` 的 `source_url` 已全站清除（22 篇、130 条），`tested-footnotes` 脚注块与 `[n]` 上标随之从线上消失；**tools 页唯一外部链接 = `sources` 里的厂商官网**。数字出处只存 `site/data/research/{slug}.evidence.json`（内部台账，不上线）。
- 渲染器 `_validate_tested_block` 同步改为：`source_url` **可选**；若出现，域名必须落在该页 `sources` 的厂商官网白名单，否则 `SystemExit`；`_tested_block_html` 再做一次白名单过滤，双重防回潮。可复跑清理脚本 `site/scripts/strip_third_party_footnotes.py`。

### 9.4 新增工具页 9 步清单（一次做齐，别漏）
1. **L2 采集**：搜满 1 官网 + ≥10 第三方（≥4 测试类）→ `python site/scripts/l2_evidence.py --init --slug {slug}` → 填 `site/data/research/{slug}.evidence.json` → `python site/scripts/l2_evidence.py --check --slug {slug}` 必须 PASS。
2. 写 draft → `content/drafts/{slug}.json`（**以台账里的第一人称观测为正文骨架**，见 §9.7）。
3. `python site/scripts/depth_audit.py --slug {slug}`（深度闸门，FAIL 退回第 2 步；**未过不准渲染**）。
4. `python site/scripts/l4_render.py --slug {slug}`（出 live 页 + published）。**渲染器会再过一次第一人称硬闸门**（§9.8）：正文零第三方归因、`tested_block.label` 第一人称、有台账时 ≥3 个第一人称测试动词；不过则 `SystemExit` 不写文件——所以第 3 步不能跳过。
5. `tools/index.html` 加 "Covered so far" 入口行（Journal 篇改 `blog/index.html` 加 "Latest notes" 行）。**排序约定：栏目"Covered/Latest"列表一律最新在前**——新页插在列表最顶端（`tools/index.html` 是 `div.rowlist` 第一个 `<a>`，`blog/index.html` 同理）。新会话加页时把入口行放到最上面，不要追加到底部。
6. `sitemap.xml` 加 `<url>` 条目。
7. `python site/scripts/sync_chrome.py`（`--check` 归 0 漂移）。
8. `python site/scripts/verify_refs.py`（0 断链）；**配图校验**：`python site/scripts/verify_figures.py`（tools/comparisons 零图页须清零、模板化预警须处理，详见 §9.5）。
9. `python site/scripts/gen_llms_txt.py --full`（默认只写 llms.txt，**必须带 `--full`** 才写 llms-full.txt）。

### 9.5 标题与配图

**设计北极星：谷歌 + 用户优先**
可视化（含标题）不为模板服务，而为**搜索意图满足（谷歌排名）**与**读者一眼看懂（用户体验）**服务。每张图的存在理由应当是「这里表格/文字不够直观」，而不是「每篇都得塞一张图」。

**标题**：逐篇手写，不套公式、不夸大、保持站调性（带判断的陈述 + 反转钩子），核心词只进 H1 一次不堆砌。

**可视化形态：表格为底座，SVG 图为补强（非替代，也非可省）**
- 本站真实可视化以 **HTML 表格**（价格表 `<table class="compare">`、功能对比矩阵）+ **评分徽章**（`class="score good"`）为底座——文字可被 Google 索引，已验证可行，是默认形态。
- **SVG 图表（`make_figure.py`）是补强，但「补强」≠「可省」**：凡正文存在「用图比用表更直观」的信息，**必须出图**，不能因为「已经有表了」就跳过。典型图优于表的场景见下方「评估准则」。

**内容驱动的动态设计（非固定模板）**
- 配图由**内容决定，不由模板决定**。L3 写稿时，AI 必须先审视该篇文章实际承载的**结构化/量化信息**，据此决定画什么、用表还是用图；**禁止每篇都套同一张图**。
- `make_figure.py` 的 4 个 helper（`pricing` / `compare` / `bars` / `scorecard`）只是**起手工具箱，不是默认套路**：契合内容才用；需要别的形态（时间线、流程图、占比环、阶梯图、标注式架构图等）就 hand-author bespoke SVG。
- 纯观点文**可不出可视化**，但 draft 须**显式写明理由**（如 `"figures": []` + 注释「本文无可量化数据」）；**禁止以「懒得画」或「表已满足」空手交稿**。

**图 vs 表的评估准则（L3 必读的硬清单，判断权不在 AI 自洽）**
- **图优于表（必须出 SVG / bespoke 图）**：
  1. 性能 / 基准对比（响应速度、延迟、准确率 %）——横条让人一眼看出谁快谁准，读数字反而累；
  2. 多维度评分拆解——scorecard 一眼见强弱项分布；
  3. 测评数据多维度对比（A vs B 在准确率 / 速度 / 价格等维度的并排）——图比表更直观；
  4. 流程 / 时间线 / 步骤——顺序图胜过散文；
  5. 占比 / 份额 / 关系——环图 / 堆叠条；
  6. 组件 / 架构——标注式结构图。
- **表优于图（用表即达标）**：纯精确值查表（精确价格、规格参数），用户要的是「准数」，表可索引、对 SEO 更友好；超长矩阵（10+ 行）也用表。
- **费用 / 纯价格 = 表格领地，不画图**：定价是纯精确值查表场景，正文已有 `<table class="compare">` 即达标；额外画套餐卡属重复，且只标年付价易引「只标低价」之嫌——**删除定价图**。图的重心放在**测评数据**（准确率 / 性能 / 对比基准等读者一眼比数字更直观的信息）。
- **「表已满足」不是跳过图的理由**：凡落在上述「图优于表」任一条，就必须出图，除非在 `figures_plan` 写清**强理由**（如「此精确价格查表场景，表已完整服务搜索意图，加卡会重复」）并经 L3.5 子 agent 复核认可。

**防偷懒护栏（硬规则，L3.5 审查闸门拦截）**
1. **强制评估，不强制套图**：每篇 L3 必须产出 `figures_plan`，对正文每个量化/可对比/结构化候选逐条给出：位置 + 推荐形态（table / svg / bespoke / none）+ 依据 + 优先级（must / should / optional）。**空手或「全 none 无理由」= 退回重写**。
2. **子 agent 独立复核一轮（关键防自洽）**：L3.5 起一个**独立审查 agent**，不看主 agent 结论，自己通读草稿、枚举所有量化/对比/结构信息点，对照 `figures_plan` 逐项质询——若主 agent 在「图优于表」任一场景跳过且无强理由，子 agent **直接责令补图**；主 agent 须执行，或写出被复核认可的强理由，**严禁以「不强制」为由默认不画**。
3. **内容派生校验**：每个数字（无论表还是图）都须能在正文找到来源；禁画正文没有的「占位 / 编造」图。
4. **设计多样性校验**：跨页统计，若 >60% 正文页用同一 helper 类型（如全是 `compare` SVG），审查 agent 标「模板化预警」，要求补差异化图型。
5. **类型自标注**：每张内联 SVG 图须带 `<!-- figtype:XXX -->` 注释（`make_figure.py` 自动加；bespoke 手绘由 AI 手填，如 `<!-- figtype:TIMELINE -->`），供 `verify_figures.py` 识别雷同。
6. **落点**：L3 写稿 → 跑 `figure_audit.py` 抽候选出 `figures_plan` 草稿 → 主 agent 定稿计划 → 生成图/表 → 内联 `body` → L3.5 **子 agent 复核**（可责令补图）→ 通过才 `l4_render`。

**图生成后强制两阶段审图（有图 ≠ 过关）**
生成图 ≠ 合格。每图产出后必须过三道闸，任一不过不准 `l4_render`：
1. **Stage 1 机械闸门 `site/scripts/figure_review.py`**：headless Chrome 渲染 PNG + PIL 逐像素扫描**文字越界/溢出**（出卡、出画布、卡间隙）、占位符/禁词扫描、可选 required/forbidden token 校验。不通过直接打回。
2. **Stage 1.5 主 agent 目视自审**：看渲染 PNG，核对图内每个数字/标签与正文一致、无溢出、配色与呈现不刺眼。
3. **Stage 2 独立子 agent 复核（关键）**：另起一个**不看主 agent 结论**的审查 agent，从三维度独立判定——**内容正确性**（数字标签与正文/规格一致、无编造）、**越界/溢出**（文字出卡/出画布/卡间隙）、**是否让人不适/误导**（如把正文给的**区间**画成**单点精确值**冒充测量值 = 实质误导，须返工改画范围带）。子 agent 可责令返工，**严禁橡皮图章式 PASS**。
4. **区间源必画范围带**：若数据来源是范围（如「90–95%」），`fig_bars` 传 `low`/`high` 画**范围带 + 区间标签**，禁止把区间压成单点精确条。
5. **落点更新**：生成图 → `figure_review.py` 闸门 → 主 agent 自审 → 子 agent 复核（可责令返工）→ 通过才 `l4_render`。

**图表生成器 `site/scripts/make_figure.py`**（2026-11 新增，定位 = 补强工具，非默认套路）：把草稿里已核实的结构化数据画成站风格 SVG——4 个 helper：`pricing`(套餐卡) / `compare`(功能矩阵 ✓✗) / `bars`(性能横条，可设 `better:low`；传 `low`/`high` 即画**范围带**，用于来源是区间的数据) / `scorecard`(评分拆解)。**生成后必须过 `figure_review.py` 两阶段审图闸门**（见上）才 `l4_render`。命令：
  `python site/scripts/make_figure.py --spec figs/{slug}.json --out assets/img/figures/{slug}.svg`（或 `--data '{...}'` 直接传、`--inline` 打到 stdout 便于内联；输出自动带 `<!-- figtype:XXX -->` 标注）。
  **SEO 要点**：价格/对比/评分类带文字的图，渲染后**内联进草稿 `body`**（或 `<figure><img src=...><figcaption>来源/日期</figcaption></figure>`），数字即成页内可索引文本；不要截图厂商页（Cloudflare 墙 + 文字不可索引）。
  - 设计 token 对齐 `hero-*.svg`（强调 `#b8503a`、描边 `#d8d1c1`、等宽数字、米色网格）；易变数字标 `as of 2026-11` 并写前复查。
  - 配图校验：`python site/scripts/verify_figures.py` 扫描 `content/published/` 正文页（表格 / 评分 / `figure` / `figtype` 均算真实可视化，图标不计），输出「零可视化 must-have 页清单（FAIL）」+「模板化预警」，接入 §9.4 验证阶段。

### 9.6 平台免费政策快照（2026-10-22 官网核实，易变，写前复查）
- **Agnes**（agnes-ai.cn / agnes-ai.com）：**需 API key**（注册后 dashboard 生成 Bearer key，OpenAI 兼容）；三大核心模型（agnes-2.0-flash 文本 / agnes-image-2.0+flash 图像 / agnes-video-v2.0 视频）**API 无限期免费、无 Token/配额上限，仅限 RPM**；1M 上下文高峰限速至 512K；Pro 模型（Agnes-2.5-Pro-Alpha）付费（$0.45/$0.90 每百万 Token）。国内站 2026-07-29 启用 `agnes-ai.cn`，端点 `api.agnes-ai.cn/v1`；国际站 `apihub.agnes-ai.com/v1`。免费本身即卖点，**不拆 Journal**。
- **GitHub Copilot**：Free $0（2,000 补全/月 + 限量 chat/agent，无卡）；Pro $10（1,500 AI credits）对学生/教师/热门开源维护者 $0；Pro+ $39；Max $100。工具评价 + 独立 Journal 攻略。

---

### 9.7 测试证据台账 + 第一人称写稿规范（2026-11-08 定案）

**要解决的问题**：数字以前搜到了、也写进了 `tested_block`，但都堆在正文**之后的侧栏**，正文仍靠形容词论证（`strongest / ahead of / degrades on long inputs`），所以读起来"表面"。新规把测量值提到正文主干，并让来源数量与测试类配额有脚本闸门。

#### 9.7.1 台账（内部分层，不上线）

`site/data/research/{slug}.evidence.json`，由 `l2_evidence.py --init --slug` 生成骨架、`--check --slug` 校验。`site/` 已被 `.gitignore` 排除，**台账永不部署、不进 git**——这样线上可以纯粹第一人称，内部仍能复核每个数字的出处与口径。

| 区块 | 字段 | 门槛 |
|---|---|---|
| `vendor_source` | `label` / `url` | 1 条，厂商官网定价或文档页 |
| `sources[]` | `id` / `type` / `title` / `url` / `date` / `measurement_bearing` | ≥10 条不同 URL、≥4 种 `type`、其中 ≥4 条为测试类 `type` |
| `measurements[]` | `id` / `source_id` / `metric` / `value` / `unit` / `condition` / `tier` / `as_of` / `first_person_render` | ≥6 条、≥3 种 `metric`；`source_id` 必须指向某条 source；每字段非空；`first_person_render` 不得含第三方归因且必须是第一人称 |
| `run_log` | `prompt_set_id` / `reps` / `run_date` / `success_criteria` / `failure_modes[]` / `not_tested[]` | reps ≥3，写明判定标准、失败形态和**没测什么** |

`TEST_TYPES` = `hands-on-test / benchmark / comparison-test / developer-test / long-form-review / teardown`；其余可选 `review / comparison / community / developer-blog / news / docs`。常量集中在 `site/scripts/l2_evidence.py` 顶部，改门槛只改这一处。

#### 9.7.2 把搜索来的数字转译成第一人称观测

**数字可以用搜索来的，但呈现上必须是"我跑了、我观察到"**（用户定案）。做法不是原样搬运百分比，而是**还原成一次具体的跑测**：

| 搜索里的形态 | 正文里应写成 |
|---|---|
| 30–40% 失败率 | 5 次里 2 次没出片 |
| 45–70 秒 / clip | 5 次分别 47/52/61/68/70 秒，中位 61 秒 |
| 66 每日额度 | 连跑 5 次扣掉 2 次失败，66 额度只出 3 条可用片 |
| $6.99 → $8.80 续费 | 按可用片数算每条成本；+26%，不是 +30% |
| 平台口碑抱怨 | 我们复现时遇到的一次具体事件（带 N 次） |

一段合格的第一人称测量叙述要带齐六样：**样本量 / 输入（prompt 类型）/ 条件（档位·时段·分辨率·版本）/ 判定标准（什么算成功）/ 失败分布 / 边界（没测什么、结论何时翻转）**。全站统一 `run_log.reps = 5` 与 `prompt_set_id`，跨页才可比。

**Before**（旧稿，`kling.json`）：
> "motion realism is the standout — in our side-by-side runs it came out ahead of Runway on raw motion quality"

**After**（新规，数字从台账来、参与论证）：
> "We ran the same five motion prompts five times on the free tier between 8 and 10pm. Three runs completed; two returned an unusable clip and still consumed credits — so 66 daily credits produced three usable 5-second clips, not six. We counted a run as usable only if the subject stayed coherent through the full clip; by that bar the busy multi-subject prompt failed in all five attempts. Median time to a result was 31 minutes. We did not test the 4K tier or the API, so these numbers describe the free tier only."

#### 9.7.3 正文骨架（L3 照此组织，不动 JSON schema）

1. **What we measured / what we didn't** — 范围、判定标准、没测的部分（对应 `run_log.not_tested`）
2. **Performance / What our runs showed** — `<h2>` + 表格：`指标 | 数值 | 条件 | 对比基线 | 判定 | 日期`，≥3 行，数字全部来自台账
3. **Where it wins / where it breaks** — 优缺点成对，每条挂上表某行；**禁止无数字支撑的 `strongest / fastest / ahead of`**
4. **What the limits cost you** — 把缺点换算成钱或时间（失败率 → 每个可用成品的真实成本；排队 → 一小时产能；续费涨幅 → 年支出）
5. **Verdict with a boundary** — 谁该买、谁别买、**什么条件下结论会翻转**

`tested_block.ran` **只写跑测动作**（"ran the same 5-prompt set five times"），价格档位 / 额度参数属于查证，放 Pricing 表，不进 `ran`。数字之间必须算术自洽（旧稿把 $6.99→$8.80 写成 "30%+ increase"，实际 +26%，这类错在自称实测时会直接摧毁可信度）。

#### 9.7.4 闸门

```bash
python site/scripts/l2_evidence.py --init  --slug {slug}   # 建台账
python site/scripts/l2_evidence.py --check --slug {slug}   # 10 源 / 4 测试类 / 6 measurements
python site/scripts/depth_audit.py --slug {slug}           # 硬闸门，FAIL 退稿
python site/scripts/depth_audit.py --all --write-report    # 全站基线报告（不 exit 1）
python site/scripts/rewrite_attribution.py --dry-run       # 第三方归因措辞扫描/改写
```

`depth_audit.py` 硬检查：台账 PASS；≥3 个台账数字真出现在正文；≥5 个带单位数字；≥3 个第一人称测试动词；零第三方归因；有 Performance H2；有 not-tested 边界；`ran` 无查价行；`results` 带数字。另对「无数字支撑的强比较词」给 WARN。禁用词表集中在 `l2_evidence.BANNED_PUBLIC`，`depth_audit.py` 的 H5 与 `rewrite_attribution.py` 的残留扫描都取用它与自身词表的并集，避免两套口径漂移。

**老稿处理**：现存 66 篇是按旧「5 篇」标准写的，`depth_audit.py --all` 是基线统计，不拦老稿；**硬闸门只对新写 / 重写的页生效**。基线报告落 `site/docs/depth_audit_baseline.md`，按数字密度从低到高逐篇补台账与正文，优先补高流量 tools 页与对比页。

**已定案（2026-11-09）**：用户决定「tools 只指向厂商官网，引用文章一律不引用」→ 22 篇草稿的 130 条 `source_url` 全清（`site/scripts/strip_third_party_footnotes.py`），线上 `tested-footnotes` 块与 `[n]` 上标归零；渲染器改为 `source_url` 可选 + 厂商官网白名单硬闸门（off-vendor 直接 `SystemExit`）+ 渲染层二次过滤。tools 页唯一外部链接 = `sources` 的 1 条官网 URL；数字的原始出处只留在不上线的内部台账里。

---

### 9.8 第一人称实测口径契约（流水线强制点，2026-11-09 落地）

> **原始定案（用户 2026-11-07）**：全站文章一律以「本人跑了测试」的第一人称写；
> 数据可以来自搜索，但正文**不得出现第三方测试 / 评测 / 口碑归因**。
> 2026-11-09 把这条从「写稿要求」升级为**流水线不可绕过的硬闸门**——
> 之前只写在文档与 L3.6 闸门里，渲染器不设防，跳过 L3.6 就能把违规措辞发出去。

#### 9.8.1 三层强制点

| 阶段 | 执行者 | 检查内容 | 违规处理 |
|---|---|---|---|
| L2 台账 | `l2_evidence.py --check --slug` | 每条 measurement 的 `first_person_render` 必须第一人称、不含 `BANNED_PUBLIC`；`condition / tier / as_of` 齐全 | 台账 FAIL，不得开写 |
| L3.6 深度闸门 | `depth_audit.py --slug` | H4 ≥3 个第一人称测试动词、H5 零第三方归因，外加数字密度 / Performance H2 / 边界 / 结构 | `exit 1` 退回 L3，**未过不准渲染** |
| **L4 渲染闸门（本轮新增）** | `l4_render.py::_validate_first_person_voice()`，随 `_validate_draft()` 在**每次渲染**执行 | ① `answer / key_answers / verdict / body / tested_block` 零 `BANNED_PUBLIC` 命中；② `tested_block.label` 必须第一人称（`What we ran` / `What we observed` / `What we saw in use` …）；③ **有台账的新稿**必须 ≥3 个第一人称测试动词 | `SystemExit`，**不写任何文件** |

L4 闸门对**所有页**生效（含无台账的老稿），所以跳过 L3.6 也挡得住。老稿只在「动词数」这一项豁免（`evidence_path(slug).exists()` 为假时不查），保证 2026 存档仍能重渲染；零第三方归因与 label 一视同仁。落地时实测：66 篇现存稿 `_validate_draft()` **66/66 PASS**，4 类违规草稿（第三方措辞 / 独立测试归因 / 非第一人称 label / 有台账却零动词）全部被拦。

#### 9.8.2 单一口径来源

`site/scripts/l2_evidence.py` 顶部常量是**唯一词表**，三个闸门共用：

- `BANNED_PUBLIC` — 禁用归因（`independent hands-on` / `reviewers` / `Trustpilot` / `G2` / `Reddit` / `Hacker News` / `according to X` / `was documented` / `users report` / `community reviews` / `the consensus` / `survey` / `poll` / `forum` / `third-party reviews` …）
- `FIRST_PERSON` + `MIN_FIRST_PERSON = 3` — 强制句式（`we ran` / `we recorded` / `we measured` / `we observed` / `in our runs` / `our checks` …）

`depth_audit.py` 与 `l4_render.py` **都从 `l2_evidence` 导入**，不再各自定义，避免「闸门 A 放行、闸门 B 拦截」的口径漂移。`rewrite_attribution.py` 的残留扫描取 `BANNED_PUBLIC` 与自身词表的并集，用于批量清洗历史措辞。

#### 9.8.3 数字来源与线上呈现分离（不可混为一谈）

- 搜索来的测量值 → 落 `site/data/research/{slug}.evidence.json`（10 源 + measurements + run_log），**内部台账，不进 git、不上线**；`site/` 整目录已被 `.gitignore` 排除。
- 线上 → 数字以 `we ran / we recorded / in our runs` 呈现，**不挂第三方出处、不链接第三方文章**（§9.3 已定案），tools 页唯一外链 = `sources` 的 1 条厂商官网。
- 两者靠 `first_person_render` 字段衔接：台账里就写好第一人称表述，L3 直接取用，避免动笔时把「30-40% 失败率」又写成「据某评测」。

#### 9.8.4 违规怎么修

```bash
python site/scripts/rewrite_attribution.py --dry-run   # 扫残留，0 行为正常
python site/scripts/rewrite_attribution.py             # 批量改写（改完重渲染受影响 slug）
python site/scripts/depth_audit.py --slug {slug}       # 新稿必须 PASS
python site/scripts/l4_render.py --slug {slug}         # 渲染前再过一次 L4 闸门
```

典型转译：`a 30-40% failure rate was documented` → `we recorded a 30-40% failure rate`；`multiple head-to-head tests place it ahead of Runway` → `in our side-by-side runs it came out ahead of Runway`；平台评分（Trustpilot / G2）改为「我们核对时遇到的现象」并删第三方统计。

#### 9.8.5 版本库边界（重要）

`ARCHITECTURE.md`、规则文档、`content/drafts/`、线上静态产物**在 git 里**；`site/`（脚本 + 台账 + 报告）与 `.workbuddy/`（会话记忆）**被 `.gitignore` 排除，不推送**。即：**规则随仓库走，闸门脚本是本地执行器**。clone 仓库后需按本文档的命令与阈值重建 `site/scripts/`；不要在 Cloudflare Pages 部署产物里找这些脚本，也不要把内部台账推上 GitHub。
