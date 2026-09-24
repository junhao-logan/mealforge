# MealForge 进度（PROGRESS）

> 本文件只保留**当前状态 + 最近 2-3 段**开发总结（回答"我做到哪了"）。
> - 完整架构决策（D/I/N/P/AI/R/F/I18N 系列）→ `DECISIONS.md`
> - 更早的逐 chat 历程 → `CHANGELOG.md`
> - 数据模型 → `docs/ERD.md`

---

## 当前状态

- **Week 12 进行中** —— 软件迭代 + 国际化 + AI 周计划增强。
- **线上**：前端 https://mealforge.pages.dev · 后端 API https://mealforge.fly.dev/docs（已部署，CI/CD 自动上线）。
- **i18n 前端全部完成**：6 页 + 所有弹窗 + 单位标签 + 日期，全部可中英切换。
- **AI 周计划增强完成**（阶段 A / A′ / B）：草稿→预览→确认入库、可现编新菜谱/新食材、跟随界面语言。
- **后端测试**：116 passed。
- **下一步**：A4/A5/A6 一组（餐次状态 ↔ 库存回补），先谈设计 —— 见 `BACKLOG.md`。

---

## Week 12 — 软件迭代 + 双语 i18n（进行中）

一批 bug/功能迭代，"一个一个改、给完整文件替换"的协作方式。已完成：

### 1. 手动创建菜谱
- 新增 `CreateRecipeDialog`（菜名 + 做法 + 配料≥1 → POST /recipes），与"AI 生成"并列。
- 配料的食材可从库里搜或**现场创建**（内嵌 `CreateIngredientForm`，避免嵌套弹窗）。

### 2. 单位系统 —— A2「单位本位」模型 ⭐（决策）
用户自建食材时可从 ~35 个单位里选一个（个/块/瓣/杯…），**按该单位填营养、按该单位计量**，不强转克。
- **落地**：Ingredient 加 `nutrition_basis_amount` + `nutrition_basis_unit` 两列；营养 = 每基准值 × 数量 / 基准量；规范单位 = `nutrition_basis_unit`。食材库/USDA 仍是克本位 `(100,'g')`，用户单位本位是 `(1,'块')`。
- **`allowed_units`** 计算属性：库存/菜谱里该食材只能选这个单位（除非当初选的就是克/ml）。`resolve_quantity()`（原 `resolve_grams`）按此换算。
- **trade-off（简历素材）**：选 A2 而非 A1（全量 quantity_grams 重命名）——在**保持营养诚实**（用户单位的营养不被伪造成克）的前提下，把改动面和回归风险降到最小。104 个后端测试全绿 + 迁移在全新库验证。

### 3. 选食材界面改 tab
加库存的选食材步骤分「全部食物 / 我的食物」两 tab + 排序（最近添加 / 字母）+ 营养预览 + **常驻"创建新食物"按钮**（不必先搜不到才创建）。后端 `list_ingredients` 加 `sort` / `scope` 参数。

### 4. 国际化 i18n —— 双语 EN/中 可切换 ⭐（决策）
**方案 C（双语可切换），默认英文。**
- **架构**：react-i18next + `en.json`/`zh.json`，key-based；语言存 `localStorage(mf_lang)`；新增账户页（Account）放语言切换开关。
- **单位标签**：value（规范单位，多为中文如"块"）**存进数据库不动**，只在 `units.js` 用英文标签表按语言显示（个/只/颗/枚 → piece）。斤/两保留罗马音。
- **日期**：`dateRange.js` 的 `weekdayLabel`/`fullDate` 改 `toLocaleDateString(locale)`，全局跟随语言。
- **翻译边界（trade-off / 简历素材）**：UI 文案 key-based 翻译 + localStorage 持久化；**明确区分"UI 文案 vs 用户/AI 生成数据"**——用户自建食材名、AI 菜谱正文保留创建语言，规避数据层双语化的成本与翻译准确性风险。
- **进度**：前端 6 页（Dashboard/Inventory/Recipes/Meal Plans/Shopping/Nutrition）+ 全部弹窗 + 单位 + 日期已全部本地化，每批 `vite build` 通过后交付。

### 5. 默认计划（Quick Log）保护
- 问题：用户删掉默认计划后，排餐下拉框变空。
- 后端 `GET /meal-plans` 列表前 `get_or_create_default_plan` **自动确保存在**；`DELETE` 遇 `plan_type='default'` 返回 400。
- 前端隐藏默认计划的删除按钮，统一显示为「Quick Log」；排餐默认选中计划。+3 测试。

### 6. 撤销已完成餐次（+ 退回库存）
- 新端点 `PATCH /meal-plans/{plan_id}/entries/{entry_id}/uncomplete`：`is_completed=False` + `restock_for_entry` + 精准失效缓存。
- **幂等设计（简历素材）**：不逐条反转，而是**按 `source_entry_id` 对流水净额聚合**，净消耗为负才回补，回补记 `reason='meal_reversal'` 反向流水。完成→撤销→再完成→再撤销循环不会重复回补；依赖 I1「零余量批次保留」才能退回原批次。+4 测试。

### 7. AI 周计划增强 ⭐（决策，见 DECISIONS D-AI5 / D-AI6）
- **阶段 A — 草稿 / 确认两步**：`POST /meal-plans/generate` 只返回草稿（除 AI 成功日志外不写库）；`POST /meal-plans/generate/commit` 才追加进目标计划（未选则新建 ai_generated 计划）。新增**食材来源**选项：任意 / 只用库存（只用库存时不硬凑，排不满就少排）。
- **阶段 A′ — 预览内嵌**：草稿直接铺进周/天视图，显示为**闪烁的绿色虚线卡片**，只能删（不改份数）；底部确认条显示「放弃 / 确认加入（N）」；目标计划在生成弹窗里**事先选好**；离开页面草稿自动抹掉。
- **阶段 B — 现编新菜谱 / 新食材**：新增**菜谱来源**选项：只用已有 / 允许现编。AI 可混用已有 variant 与 `new_recipe`，新菜谱**只在确认时入库**。
  - Grounding：给 AI 一份「可用食材 palette」（id + 名 + 规范单位，上限 80；只用库存时限定库存食材），AI 按 id 引用已有食材 → 直接用库里的准确营养。
  - 真·新食材：AI 估每 100g 营养；commit 时**按规范化名去重**（全局或本人私有），命中就复用库里的准确数据、不用 AI 估的；未命中才新建（`source='ai_generated'`，私有，克本位）。
  - 语言：prompt 要求菜名、做法、新食材名都用界面语言 —— i18n Phase 3 的「AI 按界面语言生成」已完成。
  - 草稿卡片：新菜谱带琥珀色 **New / 新** 标记。无 schema 变更，不需要迁移。+3 测试（新菜谱草稿 / commit 建食材+菜谱 / commit 按名去重）。
- **推迟到 Phase 2**（见 BACKLOG E1/E2）：食材多单位（unit_options）、USDA API 按名补准确营养。

### 协作 / 环境踩坑
- **交付方式**：完整文件打 zip。只改前端的从 `frontend/` 解压（`cp /mnt/c/Users/*/Downloads/xxx.zip ~/projects/mealforge/frontend/`）；前后端都改的从仓库根解压（`~/projects/mealforge/`）。
- **重启后启动顺序**：先开 Docker Desktop → `sudo hwclock -s` → `docker compose up -d postgres redis` → `uv run alembic upgrade head` → 后端、前端**各开一个终端**（端口被占用时 `fuser -k 8000/tcp 5173/tcp`）。
- **WSL 时钟漂移**：睡眠/重启后 Clerk 报 401「Invalid or expired token」→ `sudo hwclock -s` 对时；或 `wsl --shutdown` 重进。
- **Vite 端口回退**：5173 被占会退 5174，后端 CORS 白名单只有 5173 → CORS 报错。用 `npm run dev -- --port 5173 --strictPort` 锁死。

---

## Week 11 — 部署上线 ✅

MealForge 上线，拿到可放简历/面试的公开 URL。

- **后端**：多阶段 Dockerfile + **Fly.io**；Python 3.14 → **3.12** 收敛（部署前必做）。
- **数据**：**Neon**（托管 Postgres）+ **Upstash**（托管 Redis，作可丢加速副本，挂了退回 PG）。
- **前端**：**Cloudflare Pages**（静态 SPA + CDN），调 Fly 后端；Clerk 登录 + CORS/域名白名单打通。
- **CI/CD**：GitHub Actions —— push `main` 跑全测试（ephemeral Postgres），**测试过才部署**。
- README 重写（架构图 + 本地开发流程）；文档整合。

### 部署踩坑（简历素材）
- **Cloudflare Pages 偶发构建失败**：CF v2 构建镜像那步用 asdf 装 `.python-version`（3.12）拉插件时**网络偶发抽风**（日志 `could not read Username for github.com`），整个 build 崩、根本没到 npm/vite。**代码和配置都没问题，Retry 即可**。Root directory 已是 `frontend`。彻底根治可让前端构建不装 Python。
- 教训：**构建本地过、CF 挂 → 先看 CF build log 定位是装依赖阶段还是编译阶段**，两者修法完全不同。

---

## Week 10 — 前端 6 页全功能 ✅

React + Vite + 纯 JS + Tailwind + shadcn；6 个功能页（今日/库存/菜谱/餐计划/采购/营养目标）+ 后端配套（反向推荐三态、`/meal-plans/entries` 日历数据源、采购回流带 location/expires_at）。核心闭环（库存→AI→排餐→扣库存→采购→回流→概览）前端全打通。详见 `CHANGELOG.md` 与 `DECISIONS.md` F 系列。

---

## Backlog

完整分层待办见 `BACKLOG.md`（项目文档）。摘要：

1. **A4/A5/A6 一组**（餐次状态 ↔ 库存回补：库存区分已排未做/已完成、删除餐次退库存、零数量批次规则）—— 与 DECISIONS I1/I6 有冲突，先谈设计。
2. **A8 采购缺口去重**（与 I8 双来源相关）。
3. **i18n Phase 3 剩余**：后端错误串本地化（前端目前靠 `.includes('超出计划范围')` 匹配中文）、种子食材/分类名双语。用户自建食材名、AI 生成正文**保持创建语言**（设计边界，不改）。
4. **B4.4** AI 新食材：命中已有食材但与 AI 估算差距大时，换食材或换菜（阶段 B 未做）。
5. **Phase 2**：E1 食材多单位、E2 USDA API 补营养。

其他既有 backlog：食材搜索前缀匹配（需 pg_trgm）、AddEntryDialog 逐个查 variant 的 N+1、月视图、缓存失效第二版（variant 营养变更反查影响天）、全仓 lint 清理。
