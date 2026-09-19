# MealForge 进度（PROGRESS）

> 本文件只保留**当前状态 + 最近 2-3 段**开发总结（回答"我做到哪了"）。
> - 完整架构决策（D/I/N/P/AI/R/F/I18N 系列）→ `DECISIONS.md`
> - 更早的逐 chat 历程 → `CHANGELOG.md`
> - 数据模型 → `docs/ERD.md`

---

## 当前状态

- **Week 12 进行中** —— 软件迭代 + 国际化。
- **线上**：前端 https://mealforge.pages.dev · 后端 API https://mealforge.fly.dev/docs（已部署，CI/CD 自动上线）。
- **i18n 前端全部完成**：6 页 + 所有弹窗 + 单位标签 + 日期，全部可中英切换。
- **下一步**：Phase 3（数据/后端层的语言收口）—— 见文末 backlog。

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

### 协作 / 环境踩坑
- **交付方式**：完整文件打 zip，从 `frontend/` 解压覆盖；`cp /mnt/c/Users/*/Downloads/xxx.zip ~/projects/mealforge/frontend/`。
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

## Backlog —— Phase 3（数据/后端层语言收口）

i18n 纯 UI 文案已全绿，剩下是"数据本身的语言"：
1. **AI 按界面语言生成**（当前语言；若自由描述是别的语言就用那个）—— 改后端 prompt。
2. **后端返回的错误串**（如"超出计划范围"）—— 目前前端靠 `.includes('超出计划范围')` 匹配中文，需后端本地化后收口（代码已加注释标记）。
3. **种子食材/分类名双语**（15 个内置食材现为中文名）。
4. 用户自建食材名、AI 菜谱正文 —— **保持创建语言**（设计边界，不改）。

其他既有 backlog：食材搜索前缀匹配（需 pg_trgm）、AddEntryDialog 逐个查 variant 的 N+1、月视图、缓存失效第二版（variant 营养变更反查影响天）、全仓 lint 清理。
