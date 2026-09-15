# MealForge 开发进度

> 本文件是**执行进度快照**：记录每周做了什么、怎么做的、踩了哪些坑。
> - 架构决策与 trade-off → `DECISIONS.md`（含 D / I / AI / R / P / DEP 系列，单一真相源）
> - 数据库 schema → `ERD.md`
> - 按对话的历史开发日志归档 → `CHANGELOG.md`
>
> 只保留最近几周的执行记录；更早的已归档至 `CHANGELOG.md`。

---

## Week 10 — 前端全功能开发 ✅ 完成

**状态**:6 个功能页全部完成,前端功能完整。核心闭环(库存→AI→排餐→扣库存→采购→回流→概览)前端全打通。

### 技术栈落地
- **React + Vite + 纯 JS**(不上 TS,降复杂度)
- **Tailwind + shadcn/ui**(Base UI + Nova 预设)—— AI 生成友好、业界标准、复制源码进项目=拥有代码
- **react-router v7**(声明式 `<BrowserRouter>/<Routes>/<Route>/<Outlet>`,包名 `react-router` 非 `react-router-dom`)
- **Clerk 认证**:`useApi` hook 封装 `getToken()` 自动注入 `Authorization: Bearer`

### 文件结构(职责分层,呼应后端 app/ 分模块)
```
frontend/src/
├── main.jsx (ClerkProvider + BrowserRouter)
├── App.jsx (路由表 + SignedIn/SignedOut 保护)
├── lib/api.js (统一后端调用: base URL + token + ApiError + extractDetail)
├── lib/expiry.js (过期渐变色 + 已过期/临期标签, 纯函数)
├── lib/dateRange.js (周/天日期工具, 各视图复用)
├── hooks/useApi.js (拿 token + 调 api)
├── hooks/useDebounce.js (搜索防抖 300ms)
├── components/layout/ (Sidebar 集中 NAV_ITEMS, AppLayout Outlet)
├── components/{inventory,recipes,mealplan,dashboard,shopping}/ (各页组件)
└── pages/ (6 个页面)
```

### 6 个页面
1. **今日概览** `/` — 营养汇总(daily-summary **缓存端点**)+ 今日餐次 + 临期提醒。Promise.all 4 接口并行。复用 MealEntryCard/MacroCard。
2. **库存** `/inventory` — 模拟冰箱**三区**(常温 pantry/冷藏 fridge/冷冻 freezer)+ **未指定区**;卡片背景按剩余天数**绿→红渐变**(方案B,连续 HSL);两步式加库存(前缀搜索公共库 + visibility 分组 + 搜不到可创建);**卡片点击编辑**(数量/过期日/区域,PATCH);**已过期/临期**标签(前端 daysUntil 算,不依赖后端 expiry_status)。
3. **菜谱** `/recipes` + 详情 `/recipes/:id` — **反向推荐三态可视化**(have/partial/missing,绿勾/黄杠/红叉);我的菜谱;**AI 生成菜谱**(真调 Gemini);详情页(营养4格+配料+AI做法 instructions)。
4. **餐计划** `/meal-plans` — **天/周视图 + 周横竖切换**(4 视图,月视图留 backlog);**多 plan 管理**(建/删/筛选,层次C 默认合并+可筛选);**AI 生成周计划**;手动排餐**选 plan**;完成**扣库存**;删除。架构预留 viewMode 扩展点。
5. **采购** `/shopping` — 缺口预览(库存预扣视图);生成清单(自动算缺口);**勾选结算**(批量勾选→一次结算→每样分配**储存区+过期日**→回流);缺口**加入清单**(可调量);重算/删除。
6. **营养目标** `/nutrition` — TDEE 表单(身高/体重/年龄/性别/活动量/目标)→ PUT body-metrics → POST compute(Mifflin-St Jeor)→ 显示每日目标。设目标后今日概览进度条有基准。

### 后端增强(Week 10 配套)
- **D-R1 升级**:反向推荐从"只看有无"→"看克数"三态(have/partial/missing),返回完整食材清单 + 向后兼容 missing_count/missing_ingredients。+2 测试。
- **新增 `GET /meal-plans/entries?start=&end=`**:日历视图数据源,一次 join 查跨所有 plan 的餐次(带菜名/recipe_id),无 N+1。各视图复用。
- **add_entry 自动扩展**:超 plan 日期范围从"报 422"改"自动扩展"(与 quick-log 一致),统一排餐行为。
- **shopping purchase 加 location + expires_at**:结算回流时带储存区和过期日,回流批次直接归区(修复"回流批次无 location 落未指定区")。

### Week 10 踩坑(前端)
- **后端路由 prefix 易猜错**:nutrition=`/users/me`、shopping=`/shopping-lists`;前端拼路径前先 `grep prefix app/<domain>/router.py`
- **文件位置铁律**:代码全在 `src/`,`public/` 只放静态资源(踩过页面误放 public/pages)
- **shadcn 命令必须在 `frontend/` 跑**(先 pwd),根目录跑会误建 `next-app/`(rm -rf 删,勿 commit)
- **DialogTrigger asChild 内用 `<span role="button">`** 不用 `<button>`(button 套 button 报错)
- **shadcn destructive badge** 浅红底红字,自定义深红底要配白字
- **api 封装 put 方法**曾漏(body-metrics 用 PUT)
- **Vite 缓存**:改文件不生效时 kill 端口 + `rm -rf node_modules/.vite` 重启

### 遗留 / backlog
- 食材搜索前缀匹配(搜不到中间词,需 pg_trgm)
- AddEntryDialog 逐个查菜谱 detail 拿 variant_id(N+1,后端列表可带 variant_id)
- 月视图 + 月下钻;plan description 字段(需 model+迁移);多命名 plan 增强

### 下一步:Week 11 部署
- Python 3.14→3.12(部署前必做)
- Fly.io 部署(DEP1)+ Postgres 托管 + Redis
- 前端 build 托管;环境变量/密钥(Clerk/Gemini/DATABASE_URL);CORS/Clerk 域名白名单
- **部署不影响本地开发**:本地照常 dev/改/测,push 后线上自动更新

**Week 10 状态:前端 6 页全功能完成 ✅**

---

## Week 11 — 部署上线 ✅ 完成

**目标**:把 MealForge 部署上线,产出面试可用的公网链接。**已达成。**
**决策**:完整 DEP0–DEP9 + 部署顺序表见 `docs/DECISIONS.md` 的「DEP 系列」章节(单一真相源)。本段只记执行进度与实操踩坑。

**成果**:
- 前端 https://mealforge.pages.dev · 后端 https://mealforge.fly.dev(`/docs` 有 Swagger)
- 全链路生产可用:登录 → 加库存 → AI 生成 → 排餐 → 扣库存 → 采购 → 回流 → 概览,冒烟全通
- push main 自动测试 + 部署(CI/CD 门禁)

**11 步进度**:Step 0–10 ✅ 完成 | Step 11(自定义域名 + Clerk prod)⏸ 暂缓,非必需 | demo 账号 ⏸ 等软件迭代后再做

### 架构全景(本地三件套 → 云上三家托管)

```
你的代码 ──push main──> GitHub Actions(测试门禁)──> 通过才部署
                                                        │
前端 ─build─> Cloudflare Pages ─调用─> Fly.io 后端 ─连─> Neon(Postgres) + Upstash(Redis)
                                          │
                                    Clerk(JWT/JWKS 验签)
                                          │
                                  招聘官打开 pages.dev 即用
```

- 后端 → **Fly.io** · Postgres → **Neon** · Redis → **Upstash** · 前端 → **Cloudflare Pages** · CI/CD → **GitHub Actions**
- 云托管而非自建:免费 + 自动备份 + 免运维
- 概念澄清:Neon/Upstash 不是"替代 Postgres/Redis",它们**就是** Postgres/Redis,只是从本地容器搬到云端托管

### Step 0 ✅ — Python 版本收敛 + 配置补齐

**审计发现(与预期不符)**:①`.python-version` **根本不存在**;②CI 硬编码 `uv python install 3.12`,**本地 3.14.5 / CI 3.12 已漂移数周**;③`uv.lock` 因 `requires-python` 只有下界而生成两套分支,**280 条 cp314 wheel**(含 asyncpg/pydantic-core/sqlalchemy/cryptography)。
**修复**:双层约束——新建 `.python-version=3.12` + `pyproject.toml` 上界 `>=3.12,<3.13` + 删除重建 `uv.lock` + CI 改 `uv python install`(读文件,消除第二真相源)。
**验收**:`grep -c cp314 uv.lock` **280 → 0**,lock 头部变 `requires-python = "==3.12.*"`。
**副作用(踩坑)**:`rm uv.lock` 顺带把 **26 个依赖升到最新**(cryptography 48→50、starlette 1.2→1.6、ruff 0.15→0.16)。教训:把"版本收敛"和"依赖升级"捆进一次改动,违反 one-logical-change;更精细做法是先 `uv lock` 保留旧版再单独升级。
**顺带补**:`.env.example` 补 4 项;新建 `frontend/.env.example`(前后端 env 分离:不同运行时/注入时机/信任边界,合并会把密钥泄进 bundle)。

### Step 1 ✅ — 后端容器化(首次)

Week 1–10 后端从未进容器;Step 1 首次把应用打成镜像。**多阶段 Dockerfile**:builder 装依赖 → runtime 只拷 venv + 源码。**474MB(单阶段)→ 385MB(多阶段),-19%**。
- 降幅小恰说明底子干净(一开始就用 slim + uv),话术从"大幅优化"改为"全程控制体积"。
- 决策:①镜像内直接用 uv 不导出 requirements.txt(避免第二依赖源)②健康检查用 `/health`(liveness)非 `/health/ready`(避免 DB 抖动触发重启风暴)③非 root 运行。
- `.dockerignore` 排 `.env` 是**安全红线**(防密钥进镜像),非体积优化。
**踩坑**:`.dockerignore` 曾误存为 `.dockerignore.txt`;`docker build` 只造镜像不运行,验证需 `docker compose up` + 另开终端 curl。

### Step 2 ✅ — Neon 数据库就绪

1. **改 `database.py`**:`create_async_engine` 加 `connect_args`,**按连接目标动态决定**——识别 Neon/pooler 才 `statement_cache_size=0` + `ssl=True`,本地直连不变。原因:Neon 走 PgBouncer 事务模式不支持 prepared statement;本地直连时它是有益优化,全局关掉是白白损失(面试点:懂"为什么关"而非抄 workaround)。asyncpg 不认 URL 的 `?sslmode=require`,须 `connect_args` 传 `ssl=True`。
2. **建表**:本地临时指向 Neon 跑 `alembic upgrade head`,13 迁移一次过(→ `d5a8c3f10e29 head`)。
3. **灌种子**:15 种 USDA 食材。
**关键理解**:迁移/种子都从本地做(一次性初始化,建好长期存在);USDA 原始 CSV 永不上云(只是加工原料);Neon(云库,一直在)vs `.env.neon`(本地临时便条,用完即删防泄露)是两回事。
**安全踩坑**:`.gitignore` 原规则不匹配 `.env.neon`,已追加规则 + `git check-ignore` 验证;临时环境用 `env $(...)` 单命令加载,不改本地 `.env`。

### Step 3 ✅ — Upstash Redis 就绪

- 建云 Redis,连接串 `rediss://`(两个 s,TLS)。**代码零改动**——redis-py 见 `rediss://` 自动启 TLS,Week 9 的降级设计(cache.py 全 try/except)本就为此准备。
- **降级实证(简历素材,已采集)**:故意用坏 Redis 端口(6379→16379)启动后端,`Application startup complete` + `/health` 200 → **Redis 不可达时服务照常启动、健康**。这是 D-P3 优雅降级的真实环境验证,比本地 fakeredis 有说服力。
- 坑:Upstash 的 REST 凭据(`https://` + token)≠ Redis 协议连接串(`rediss://`),初次容易复制错。

### Step 5 ✅ — Fly 后端上线(本周最硬一关,一次过)

- 装 flyctl → `fly launch --no-deploy` → 用备好的 `fly.toml` 覆盖 → 灌 secrets → `fly deploy`。
- **`fly.toml` 关键配置**:`min_machines_running=1`(DEP7,避免招聘官遇冷启动白屏)、健康检查 `/health`、`release_command = "alembic upgrade head"`(DEP6,每次部署自动迁移)、region `iad`(对齐 Neon/Upstash 美东)。
- **secrets 格式坑(前面踩过,这次一次填对)**:DATABASE_URL 要 `postgresql+asyncpg://` 前缀 + **去掉** `?sslmode=require&channel_binding=require`(asyncpg 不认,尤其 channel_binding 会直接报错);REDIS_URL 的 `rediss://` 原样保留。共 4 个 secret(DATABASE_URL/REDIS_URL/CLERK_ISSUER/GEMINI_API_KEY)。
- 验证:`/health` + `/health/ready` 均 200,release_command 里 alembic 正常连库(Neon 已 head,秒过)。

### Step 6 ✅ — 前端上线 Cloudflare Pages

- 连 GitHub 自动部署(顺带把 Step 9 前端侧的 CD 做了)。**新建 `frontend/public/_redirects`**(`/* /index.html 200`)—— SPA fallback,否则直访 `/recipes/12` 会 404(react-router 客户端路由)。
- **Cloudflare 配置**:Root directory=`frontend`、Build command=`npm run build`、Build output=`dist`;环境变量 `VITE_CLERK_PUBLISHABLE_KEY` + `VITE_API_URL=https://mealforge.fly.dev`(无尾斜杠,build-time 注入)。
- **踩坑**:①先误入 Workers(`npx wrangler deploy`)而非 Pages,退出重选 Pages 入口;②首次 build failed —— Build command 框空着没填,导致没跑 build、`dist` 不存在。补上 command 即过。

### Step 7 ✅ — 打通前后端(登录成功)

- **只改一个 secret**:`fly secrets set CORS_ALLOWED_ORIGINS_RAW="https://mealforge.pages.dev"`(https、无尾斜杠、只放正式域名不放预览 hash 域名)。`fly secrets set` 自动触发重新部署。
- **azp 不用设**:auth 代码逻辑是"`CLERK_AUTHORIZED_PARTIES_RAW` 留空则跳过 azp 校验",Fly 没设它 = 跳过 = 减少变量。那个悬了多轮的"Clerk dev 能否加域名"问题就此化解——不走 azp 就不需要答案。
- **验证**:pages.dev 登录成功 = 前端→CORS→Clerk 验签→JIT 在 Neon 建用户影子行 全链路通。Clerk dev instance 对 pages.dev 确实宽松(那个老问题的实际答案)。

### Step 8 ✅ — 端到端冒烟

核心业务全链路在生产走通(加库存/AI 生成/排餐/扣库存/采购/概览)。功能无故障,余下是界面/交互小瑕疵(设计层,不阻塞上线,慢慢改)。

### Step 9 ✅ — CI/CD 测试门禁

- `.github/workflows/fly-deploy.yml`:push main → **先跑 93 测试(against ephemeral Postgres)→ 通过才部署 Fly**。`deploy` job `needs: test` 是门禁关键;`concurrency` 防并发部署踩踏;`--remote-only` 在 Fly 侧构建。
- 删掉冗余的旧 `ci.yml`(测试已并进 deploy workflow)。`FLY_API_TOKEN` 存 GitHub Secrets,不落代码。
- **顺带发现**:这次 commit 才把 `fly.toml` 加进 git(之前一直只在本地)——意味着此前的自动部署读不到精心配的 fly.toml,用的是 Fly 缓存的旧配置;现在提交后 CD 才真正用这份配置。
- 两个 job 全绿,CD 闭环成立。

### Step 10 ✅ — README(成品定位)

- 重写 README:删掉过期内容(Week 4 进度、TypeScript/Celery/Claude API 三个不存在的技术),换真实栈,加架构段 + 在线链接,成品定位不留学习痕迹,去 emoji。删了指向已删除 `ci.yml` 的坏 badge。

### Step 11 ⏸ — 自定义域名 + Clerk production(暂缓)

- 非必需:dev instance + pages.dev 已能正常登录演示。要更专业(自定义域名 + `pk_live_`)时再做,DEP5 阶段二有预案。

### 简历素材(已采集)

| 数据 | 值 |
| --- | --- |
| 依赖树收敛 | `uv.lock` cp314 条目 280 → 0 |
| Docker 镜像 | 474MB → 385MB (-19%),多阶段 + 非 root |
| 优雅降级实证 | 坏 Redis 端口下后端仍启动 + `/health` 200(D-P3 线上验证) |
| CI/CD | push main → 93 测试门禁 → 自动部署 Fly |
| 部署架构 | 前端 CDN + 后端容器 + 托管 PG/Redis + 托管认证,全免费层 |

**待补采(需线上实测)**:daily-summary 缓存命中 vs 未命中 p50/p95、Neon 冷启动耗时、月总成本、CI/CD 端到端时长。

### Week 11 踩坑速查

- **secrets 格式**:DATABASE_URL 去 `?sslmode`/`channel_binding` + 加 `+asyncpg`;REDIS_URL 保 `rediss://`。
- **Cloudflare**:别进 Workers,要 Pages;Build command 必填;Root=`frontend` / output=`dist`;必配 `_redirects` SPA fallback。
- **CORS**:只放正式 pages.dev 域名(预览 hash 域名会被拦);https + 无尾斜杠。
- **fly.toml 要进 git**:否则 CD 读不到,用 Fly 缓存的旧配置。
- **终端提示符别复制**:`user@host:~$` 是提示符不是命令,只复制 `$` 后面部分。

### 下一步(Week 11 后)

1. **软件迭代**:冒烟发现的界面/交互小瑕疵(设计层);Week 10 backlog(pg_trgm 前缀搜索、月视图、AddEntryDialog N+1)。
2. **demo 账号**:迭代稳定后做——预置数据的 demo 账号写进 README,或录 30s GIF(招聘官不会注册)。
3. **DECISIONS 补 DEP9**(CI/CD 测试门禁)那一条。
4. **线上实测**补齐上面几个简历数字。

**Week 11 状态:部署上线全部完成 ✅ — MealForge 已是公网可访问、自动部署、带测试门禁的完整生产应用。**