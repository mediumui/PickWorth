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

整条流水线（`tools/` 里的脚本）产出**关键词与素材**，**我（本子 agent）负责把素材写成英文正文**，
再渲染成静态页。分工如下：

```
L0  动态种子     l0_seed_fetch.py   HF 新模型 + PH 新工具  →  tools/seed-pool.json
                      │ （免费源，天天有新词）
L1  扩词+打分   l1_kwinside_scorer.py  用 Kwinside 拉相关词+月搜索量，
                      │                按 量/长尾/商业意图 打分排序  →  tools/keyword-pool.csv
L2  素材可写性  门槛：该词对应的工具/模型 要有 官方 docs + ≥5 篇第三方测评
                      │                （越多越好）；不满足则换词
L3  写正文       我  提炼 20+ 素材 → 优点/缺点/对比表/结论/配图清单/内链（英文）
                      │                落到  content/drafts/{slug}.json 或 .md
L4  合规+渲染   合规自检（合成非拼贴、配图官方/自制、出处标注）
                       渲染成  content/published/{slug}/index.html
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
├── tools/
│   ├── l0_seed_fetch.py       L0 动态种子（HF + PH）
│   ├── l1_kwinside_scorer.py  L1 Kwinside 扩词打分（key 已按要求写死在脚本内）
│   └── (未来) l2_material_gate.py / l4_render.py
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
> - `tools/l4_render.py`：读 `content/drafts/{slug}.json` → 填模板 → 写 `content/published/{section}/{slug}/index.html` 并同步到线上目录树。`{{ROOT}}` 前缀按目标深度自动补 `../`。
> - `tools/draft_from_page.py`：把已写好的线上页反向抽回 draft JSON，让旧文章也能走新流水线。
> - `tools/sync_chrome.py`：让 `_chrome.html` 成为**全站** chrome 的唯一来源（见 §5.1）。
> 全站 28 页由模板/同步产出（`verify_refs` 28 页全过、0 中文、0 emoji、`robots=index`）。

---

## 5.1 站点 chrome：单一来源（`_chrome.html`）

页头、页脚、图标 sprite、移动端底部 tab **只在 `src/components/_chrome.html` 里维护一份**。
改一处，跑一条命令，全站 28 页一起更新——不需要逐个文件手改。

```
编辑 src/components/_chrome.html
python tools/sync_chrome.py          # 全站页内替换
python tools/sync_chrome.py --check  # CI / 提交前用：有页过期就 exit 1
python tools/sync_chrome.py --dry-run # 只看会动哪些文件，不落盘
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
  仓库可只放**生成产物 + 静态页**，`tools/` 的挖词脚本与 key 留在本地（不进公开仓库）。
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
2. `python tools/l4_render.py --slug {slug}`（出 live 页 + published）
3. `tools/index.html` 加 "Covered so far" 入口行（Journal 篇改 `blog/index.html` 加 "Latest notes" 行）。**排序约定：栏目"Covered/Latest"列表一律最新在前**——新页插在列表最顶端（`tools/index.html` 是 `div.rowlist` 第一个 `<a>`，`blog/index.html` 同理）。新会话加页时把入口行放到最上面，不要追加到底部。
4. `sitemap.xml` 加 `<url>` 条目
5. `python tools/sync_chrome.py`（`--check` 归 0 漂移）
6. `python tools/verify_refs.py`（0 断链）
7. `python tools/gen_llms_txt.py --full`（默认只写 llms.txt，**必须带 `--full`** 才写 llms-full.txt）

### 9.5 标题与配图
- 标题**逐篇手写**，不套公式、不夸大、保持站调性（带判断的陈述 + 反转钩子），核心词只进 H1 一次不堆砌。
- 配图**按需不硬塞**：数据 / 文字 / 排版图（额度表、能力阶梯）→ 本地 SVG/HTML 手绘（与 `hero-*.svg` 同风格，数字可控）；纯氛围 og 图才用 AI 生图（帧刻 `tools/vidshell_image_gen.py`，Bearer 走 `VIDSHELL_VK` 运行时注入，不落盘）。

### 9.6 平台免费政策快照（2026-10-22 官网核实，易变，写前复查）
- **Agnes**（agnes-ai.cn / agnes-ai.com）：**需 API key**（注册后 dashboard 生成 Bearer key，OpenAI 兼容）；三大核心模型（agnes-2.0-flash 文本 / agnes-image-2.0+flash 图像 / agnes-video-v2.0 视频）**API 无限期免费、无 Token/配额上限，仅限 RPM**；1M 上下文高峰限速至 512K；Pro 模型（Agnes-2.5-Pro-Alpha）付费（$0.45/$0.90 每百万 Token）。国内站 2026-07-29 启用 `agnes-ai.cn`，端点 `api.agnes-ai.cn/v1`；国际站 `apihub.agnes-ai.com/v1`。免费本身即卖点，**不拆 Journal**。
- **GitHub Copilot**：Free $0（2,000 补全/月 + 限量 chat/agent，无卡）；Pro $10（1,500 AI credits）对学生/教师/热门开源维护者 $0；Pro+ $39；Max $100。工具评价 + 独立 Journal 攻略。
