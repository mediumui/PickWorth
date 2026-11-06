# PickWorth — 网站架构

> 英文 AI 工具测评 + 对比站（`pickworth.top`）。静态站，零构建，Cloudflare Pages 自动部署。
> 本文是项目的"架构说明书"，落地目录即 `D:\WorkBuddy\pickworthhq\`。

---

## 1. 一句话定位

**"读 20+ 篇素材，提炼式综合（synthesis）出一篇带对比表和结论的测评"**，靠高搜索 / 低竞争 / 长尾词起量，广告 + 联盟变现。
- 合法边界：**可以汇总事实、可以对比、可以加自己的测试层与结论；不可逐字改写 / 拼贴他人原文**。
- 每个论断都要能溯源到出处（`sources` 列表 + 文中引用）。

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
L2  素材可写性  门槛：该词对应的工具/模型 要有 官方 docs + ≥5 篇第三方测评
                      │                （越多越好）；不满足则换词
L3  写正文       我  提炼 20+ 素材 → 优点/缺点/对比表/结论/配图清单/内链（英文）
                      │                落到  content/drafts/{slug}.json 或 .md
L4  合规+渲染   合规自检（合成非拼贴、配图官方/自制、出处标注）
                       site/scripts/l4_render.py 渲染成  content/published/{slug}/index.html
                       Cloudflare Pages 自动部署
```

**额度账（Kwinside 20 次/天）**：一天 2–3 篇 × 每篇 1 次 ≈ 5–6 次，富余 14+。
**关键合规点**：
- 正文是"读 N 篇 → 提炼共识与分歧 → 加自己的测试层 → 给结论"，**不是把别人 20 篇拼接**。
- 配图用官方截图 / 自制示意图，**不盗他人测评里的截图**。
- 每个"据称/报告"类论断后跟来源链接。

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
- [ ] 关键词确实 ≥5 篇第三方素材支撑（L2 门槛）

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
- 每篇 = **1 篇官网权威**（定价 / 免费额度数字的最终来源）+ **≥5 篇第三方交叉**（独立评测站 / Reddit / HN / 开发者博客 / 竞品对比文，类型尽量多样）。
- 提炼三层：①共识 → good/limits；②分歧（额度够不够、模型质量、vs 竞品）→ 正文点出并给判断；③官网不会写的边界（实际 RPM、高峰表现、认证坑、隐私、真实体验）→ limits + 1–2 条"用户实测反馈" key_answers。
- **免费额度数字必须官网 pricing 页核实，易变数字（RPM / 聊天条数 / 积分 / 1M 上下文高峰限速）写判断不写死**。
- 第三方来源**不进 `sources` 字段**（`sources` 只留厂商官网 1 条，见 §9.3）；第三方只用于正文提炼。
- **动笔前先搜满 5 篇第三方，提炼完再写**，避免"满篇官网腔"。

### 9.3 Sources 引用策略（少而精）
- `sources` 只留**第一方 / 厂商官网** URL（产品自身价格页 / 文档页）；**不写** pickworth.top 站内自引用；**不用**裸 API 端点。
- **非 tools 页**（comparisons / lists / blog）一般**不带** `sources` → 渲染器自动省略 Sources 区块。
- 每条 source 必须是 `Label — https://url`（末位 token 为合法绝对 URL），否则 `_validate_sources` 渲染前 `SystemExit`。

### 9.4 新增工具页 7 步清单（一次做齐，别漏）
1. 写 draft → `content/drafts/{slug}.json`
2. `python site/scripts/l4_render.py --slug {slug}`（出 live 页 + published）
3. `tools/index.html` 加 "Covered so far" 入口行（Journal 篇改 `blog/index.html` 加 "Latest notes" 行）。**排序约定：栏目"Covered/Latest"列表一律最新在前**——新页插在列表最顶端（`tools/index.html` 是 `div.rowlist` 第一个 `<a>`，`blog/index.html` 同理）。新会话加页时把入口行放到最上面，不要追加到底部。
4. `sitemap.xml` 加 `<url>` 条目
5. `python site/scripts/sync_chrome.py`（`--check` 归 0 漂移）
6. `python site/scripts/verify_refs.py`（0 断链）；**配图校验**：`python site/scripts/verify_figures.py`（tools/comparisons 零图页须清零、模板化预警须处理，详见 §9.5）
7. `python site/scripts/gen_llms_txt.py --full`（默认只写 llms.txt，**必须带 `--full`** 才写 llms-full.txt）

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
