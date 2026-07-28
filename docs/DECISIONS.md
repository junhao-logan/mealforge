# MealForge 设计决策记录

> 本文件是所有架构决策的**唯一记录处**（single source of truth）。
> 记录内容：决策本身、理由、备选方案，以及后续实现中的**修订**。
> 决策编号：`D` = 环境与架构（Week 1-4，含 D/N/P 系列），`I` = 库存与采购（Week 5+）。
> 设计在实现中演进是正常的 —— 修订会保留原条目并标注，不做无痕修改。

## 目录

- [D 系列 — 环境与架构决策（Week 1-4）](#d-系列--环境与架构决策week-1-4)
- [修订记录](#修订记录)
- [I 系列 — 库存与采购决策（Week 5+）](#i-系列--库存与采购决策week-5)
- [技术债](#技术债)
- [流程笔记](#流程笔记)

---

## D 系列 — 环境与架构决策（Week 1-4）

> 共 57 条，按日期排列。含 D1-D7（数据模型）、N1-N4（营养）、P1-P4（餐食计划）等编号决策。
> 其中 5 条已在 Week 5 实现时修订，见下节。

| 日期 | 决策 | 理由 | 备选方案 |
| --- | --- | --- | --- |
| 2026-05-13 | 开发环境选 Windows + WSL2/Ubuntu 22.04 | 部署目标是 Linux，本地用 Linux 保证一致性；避开 Windows 上 uvloop 等库的兼容问题 | 纯 Windows、Mac、Linux 双系统 |
| 2026-05-13 | Python 工具链选 uv | Rust 实现速度快 10-100 倍、统一替代 pip/poetry/pyenv/virtualenv、海外新项目主流 | pipenv（维护乏力）、poetry（更新慢）、pip+venv（手动管理累） |
| 2026-05-13 | Node 通过 nvm 安装而非 apt | apt 源里的 Node 版本过老（12.x，已 EOL）；nvm 支持多版本切换便于回退 | apt install、NodeSource 源、fnm |
| 2026-05-13 | 用 Node 24 LTS | 当前最新 LTS（Active LTS 阶段），30 个月支持周期 | Node 22（前一代 LTS）、Node 20（更稳） |
| 2026-05-13 | Docker 用 Docker Desktop + WSL Integration，不在 Ubuntu 独立装 | 一次配置 Windows/WSL 共用 Engine；Docker Desktop 个人用户免费；管理方便 | WSL 里独立 apt install docker.io |
| 2026-05-13 | 代码放 `/home/junhao_logan/`，不放 `/mnt/d/` | WSL 原生文件系统比挂载的 Windows 盘快 10 倍，npm install/docker build/git 都受益 | 放 D 盘方便 Windows 端访问 |
| 2026-05-13 | 项目目录用 `~/projects/mealforge` | `~/projects` 集中放所有项目，符合行业惯例；不放 `/mnt/d` 避免文件系统慢 10 倍 | 直接放家目录、放 D 盘 |
| 2026-05-13 | GitHub 仓库选 Monorepo（前后端同仓） | 个人项目前后端强耦合；招聘官点一个链接看全部；docker-compose 统一启动 | 双仓库分离 |
| 2026-05-13 | 用 SSH key 而非 HTTPS + PAT 跟 GitHub 通信 | 配一次永久无密码；私钥不外传比 PAT 安全；服务器运维必备技能 | HTTPS + Personal Access Token |
| 2026-05-13 | SSH key 算法选 ed25519 | 2014 后的最佳选择，短、快、安全；GitHub 推荐 | RSA 4096（兼容性更好但更长） |
| 2026-05-13 | SSH key 不设 passphrase | 个人开发机物理被偷概率低；git 操作完全无感更顺 | 设 passphrase + ssh-agent 缓存 |
| 2026-05-13 | Conventional Commits 规范（feat:/fix:/chore: 等）从第一个 commit 开始用 | commit history 像产品、未来可自动生成 CHANGELOG | 自由格式 commit message |
| 2026-05-13 | 项目骨架走"最小起步"路线，不一次性建完整目录 | commit history 看着像"持续工作"而非一次性堆完；学习曲线更平缓；每步都能跑 | 一次性建完整 Monorepo 结构 |
| 2026-05-13 | README 用纯文字 + 粗体，不用 badges | 干净专业，避免"入门项目堆 badges"的廉价观感 | 满屏 badges |
| 2026-05-13 | License 选 MIT | 最宽松最常见，海外项目标配；不影响商用未来扩展 | Apache 2.0、GPL |
| 2026-05-19 | 食材份量统一存克数，UI 单位元数据下放到 Ingredient 表 | 营养计算 O(1) 算术；与 USDA per-100g 数据天然对齐；用户输入体验不损失（default_unit + grams_per_unit）；跨菜谱营养汇总简单 | 在 RecipeIngredient 上存原始单位 + UnitConversion 表（N+1 查询噩梦） |
| 2026-05-19 | 库存采用 Snapshot + Event Log 双写架构 | 读路径 O(1)，事件流支持时间点回放、消耗趋势、临期预测；对账机制可检测漂移；是真实生产系统常见做法 | 纯 CRUD 覆写 quantity（丢历史）、纯事件溯源（读慢） |
| 2026-05-19 | 库存不足不阻断，记 shortage_grams 字段；inventory_items.quantity_grams CHECK ≥ 0 | 用户体验流畅；自动喂入"急需采购"建议；语义清晰（库存永远 ≥ 0） | 允许 quantity 为负（语义怪）、硬阻断（用户体验差） |
| 2026-05-19 | MealPlan 任意起止日期 + 允许重叠 + plan_type 字段 | 支持任意周期（周/月/5 天冲刺）；模板和实际计划可并存；用户灵活分类 | 固定周一到周日（不够灵活）、DB 强制不重叠（用户难用） |
| 2026-05-19 | Recipe → RecipeVariant 两级抽象，食材挂 Variant | 一个菜可有多种做法（经典/减脂/增肌）；AI 可生成"已有菜谱的减脂变体"；产品体验更好 | 单层 Recipe + parent_recipe_id 软关联（搜索体验差） |
| 2026-05-19 | purpose_tag 固定枚举 + recipe_variant_tags 自由标签的双层混合 | 核心分类强约束（保证 AI 理解、筛选、统计）；个性化标签完全自由；产品和用户决策权分明 | 完全自由文本（拼写漂移污染筛选）、纯固定枚举（用户表达力受限） |
| 2026-05-19 | 营养信息缓存到 recipe_variants 表 + 同步/异步混合 invalidation | 读路径零计算；21 餐 × 5 食材的周聚合从 100+ JOIN 降到 21 次直接读；nutrition_computed_at 兜底排查 | 实时算（每次 JOIN，N+1 风险） |
| 2026-05-19 | AI 调用独立 ai_generation_logs 表，prompt_input_hash 作缓存键 | 支撑限流、prompt A/B、输出缓存（预期节省 60% LLM 成本）、成本看板、失败率监控 | 把 AI 字段直接挂到 Recipe 表（数据混乱、无法分析） |
| 2026-05-19 | inventory_transactions 同时记 occurred_at（事件发生）和 created_at（DB 写入） | 支持用户事后补录（"我中午做的饭刚想起来记一下"），时间点回放查询走 occurred_at 才正确 | 只记 created_at（补录数据会错位） |
| 2026-05-19 | meal_logs 暂不建表，MVP 用 meal_plan_entries.is_completed 替代 | 减少 Week 1-4 实现负担；等真用起来观察用户偏离计划的模式再演化；演进式设计本身是简历故事 | Week 1 就建 meal_logs 表（前 4 周用不上） |
| 2026-05-19 | notes.rating 是 1-10 主观评分，语义由用户自定义 | 不强加单一维度（好吃 / 难度 / 满意度由用户决定）；产品决策权下放 | 固定"好吃程度 5 分制"（限制用户） |
| 2026-05-30 | 目录结构走 domain-driven（按领域：core/health/...，后续 auth/recipes/inventory/ai） | 10+ 领域模块按层划分会很乱；相关代码同目录、重构友好；fastapi-best-practices 推荐；面试叙事更专业 | layered（按层：api/models/schemas/services） |
| 2026-05-30 | ORM 用 async（asyncpg + AsyncSession + SQLAlchemy 2.0） | 与 FastAPI async-first 一致；后续 AI 调用是多秒级 I/O，async 让 worker 等待时处理别的请求；海外 SDE 基础要求 | sync（psycopg2 + Session，需 run_in_threadpool 包一层） |
| 2026-05-30 | 依赖管理用 pyproject.toml + uv（PEP 621），app 以 hatchling editable 装入 venv | 海外主流、uv 原生支持；editable 安装保证 import app 不受 cwd/sys.path 影响 | requirements.txt、uv workspace |
| 2026-05-30 | Alembic 走 async 模板，单一 asyncpg driver | 全栈只用一个 driver，不必为迁移装 psycopg2、不维护两套连接串；代价是 env.py 略复杂（一次性） | 同步迁移（psycopg2，双 driver） |
| 2026-05-30 | Base.metadata 挂 naming_convention（ix/uq/ck/fk/pk） | 约束名确定可读，autogenerate diff 干净、downgrade 能精准点到约束名；15 张表建完再补是迁移灾难 | 用 SQLAlchemy 默认隐式约束名 |
| 2026-06-02 | 认证用托管 Clerk 而非自撸 JWT | 自撸 auth（密码哈希/重置/邮箱验证/OAuth/session 撤销/防爆破）高风险低回报、面试不加分；精力留给 AI + 库存差异化；免费 50k MAU | 自撸 JWT（fastapi-users / 纯手写）、Auth0 |
| 2026-06-02 | Clerk over Supabase Auth | 栈已 commit 自托管 Postgres + SQLAlchemy + Alembic；Supabase Auth 的 RLS 红利（auth.users 与业务表同库）用不上、反成 split-brain；Clerk 是独立身份层，契合现状 | Supabase Auth |
| 2026-06-02 | users 表用 identity shadow（业务 FK 指 internal UUID，非 Clerk ID） | 第三方身份与本地领域用户解耦；换 provider 只重映射影子表一列，业务表不动；clerk_user_id 作锚点 | 直接拿 Clerk user id 当 PK（provider 锁定） |
| 2026-06-02 | JIT user provisioning（webhook 延后） | 首鉴权请求 upsert 影子行，免 webhook 投递可靠性/乱序/本地隧道；删除同步等需要时再补 user.deleted webhook（演进式设计） | 启动即 webhook 全量同步 |
| 2026-06-02 | networkless JWT 验证（JWKS 公钥本地验签 + 缓存） | 延迟低、避开 API 限流；自己用 PyJWT 验 iss/azp/exp，面试能讲清原理；run_in_threadpool 不堵事件循环 | 每请求调 Clerk authenticate API、SDK 黑盒验 |
| 2026-06-02 | per-domain 增量 migration（非一次性建 15 表） | ERD 是蓝图、按域逐步物化；migration history 可 review、像持续工作；避免一堆空表 | big-bang 一次建完 15 表 |
| 2026-06-02 | clerk_user_id 仅 unique 不加 index | Postgres 唯一约束自带索引，再加 index 造成重复索引 | 额外 index=True |
| 2026-06-02 | dev 阶段 azp 校验留空跳过 | 无前端时用裸 token/Backend API 测、azp 来源不固定；接前端后填 origin 再启用 | dev 即强制 azp |
| 2026-06-16 | USDA 子集 = Foundation Foods 2025-12 + SR Legacy 精选；CSV 快照、版本钉死、不走实时 API；精选 200–400 条通用食材 | seed 是一次性可复现离线动作，CSV 快照保证确定性+无网络耦合+无限流；Foundation 新质量高但覆盖窄、SR Legacy 广但 2018 冻结，二者互补；精选子集搜索干净、seed 快、可扩 | 实时 API（运行时耦合网络+限流）、全量 7800 条（稀释搜索）、含 Branded（百万级噪声污染搜索） |
| 2026-06-16 | 营养锁四宏量 kcal/protein/fat/carb，numeric nullable，不设非 NULL 默认值；energy 取值优先级 1008→2048→2047 单位锁 kcal | 0 ≠ unknown，NULL 才能表达"无数据"（避免给控钠/控糖用户错误信息）；USDA 一条食材可能多行 energy（SR 用 1008、Foundation 常见 Atwater 2047/2048），定确定性优先级保证跨数据集一致；幂等 seed 让延迟加列零成本 | 全字段 NOT NULL（语义错）、默认值填 0（把 unknown 谎报成 0）、一次性全加 100+ 营养素（列爆炸） |
| 2026-06-16 | seed 走独立幂等脚本（非 Alembic data migration），usda_fdc_id 作 upsert key（ON CONFLICT DO UPDATE）；人工单位字段与 USDA 营养字段分离更新 | schema migration 只管结构、不背批量参考数据；fdc_id 全球唯一稳定，重跑安全；分离更新避免重灌冲掉手工裁决的 default_unit/grams_per_unit | 把 seed 塞进 data migration（文件臃肿、downgrade 删数据语义乱）、name 作 key（不稳定） |
| 2026-06-16 | grams_per_unit 用单列 NUMERIC（方案 a），每食材一个非克单位 + 克兜底；手工填 + foodPortions 机会性参考；多单位等 Phase 2 unit_options 表 | MVP 真实需求是"每食材一个好用单位 + 克兜底"（鸡蛋→个、米→杯、肉→克），单列够用；foodPortions 脏（modifier 自由文本）不盲信，精选子集让人工裁决可行；JSONB 多单位会增加 D7 查询复杂度且提前打乱 ERD 演进 | 现在上 JSONB 多单位（过早抽象）、全量 import foodPortions（脏数据污染单位下拉）、UnitConversion 表（ERD 已否决，N+1） |
| 2026-06-16 | USDA 子集 = Foundation Foods **2026-04-30** + SR Legacy 2018-04 精选；CSV 快照、版本钉死、不走实时 API；精选 200–400 条通用食材 | （理由同前）实际下载版本为 2026-04-30（锁决策后 USDA 又发新版），版本号以硬盘真实快照为准 | （同前） |
| 2026-06-16 | 原始 USDA CSV gitignored，不进 commit；可复现性靠「决策表记录的发布版本 + manifest 里的 fdc_id」双重兜底 | fdc_id 全局稳定（D3），即便重下新版，manifest 的 fdc_id 仍解析到同一批食材，仅营养数值可能微调；原始 CSV 体积大、不宜入库 | 把原始 CSV 也 commit（仓库臃肿）、纯靠版本号（CSV 不在库无法核对） |
| 2026-06-16 | seed upsert（S4）= 方案 a 全刷：ON CONFLICT DO UPDATE 同时刷营养 4 列 + 单位 4 列（name/category/default_unit/grams_per_unit） | manifest + USDA 快照是唯一 SoT，"改 manifest→重跑→DB 同步"心智模型最简；D3 设想的"人工/营养分离"在 manifest 架构下已天然实现（单位来自 committed manifest、营养来自 CSV，物理分离），无需 SQL 层再分离；MVP 无"用户编辑 seed 食材"功能 | 方案 b 只刷营养（单位冻结，改 manifest 不生效）、方案 c 全刷+WHERE source='usda' 守卫（防用户改动被冲，但防的是不存在的风险，过早抽象） |
| 2026-06-17 | D5：RecipeIngredient 存份量 = 方案 B（归一化 quantity_grams + 用户原始 input_amount/input_unit 双存）；写入时换算（input_amount × grams_per_unit），单位限 default_unit 或克（D5a） | 克数供 O(1) 营养聚合、与 USDA per-100g 对齐；同存原始输入供友好显示（"2 个"而非"100g"）；单位约束直接由 D4"单 default_unit + 克兜底"推导，不引入多单位换算表 | 方案 A 只存克（丢显示语义）、方案 C 只存原始单位（读时现算，N+1，ERD 已否决） |
| 2026-06-17 | D6：营养聚合 = 独立 service（compute*variant_nutrition）+ 配料变动时同步算 + 缓存回写 RecipeVariant（total*\* + nutrition_computed_at）；NULL 传播为"不完整"不当 0；异步批量重算留 Phase 2 | 配料就几条，同步聚合毫秒级，无需异步；NULL 传播延续 D2 的 0≠unknown 到聚合层，避免 unknown 误当 0 误导用户；异步价值在 Phase 2 食材更新批量重算场景 | 一上来就上异步（过早）、NULL 当 0 加（语义错） |
| 2026-06-17 | D7：读取份量直接显示 input_amount/input_unit，quantity_grams 仅供计算 | D5=B 的自然结果——写时换算一次、读时零换算；memory 里"换算查询时机"顾虑就此消解 | 读时反算（多余）、ERD 原稿方案 A 无原始单位可显示 |
| 2026-06-18 | N1：BMR 用 Mifflin-St Jeor；活动系数标准 5 档；目标热量 TDEE±默认增减（减脂−500/维持0/增肌+400）可由 calorie_delta 覆盖；宏量蛋白按体重 2g/kg + 脂肪 25% 热量 + 碳水填余 | Mifflin-St Jeor 不需体脂率（降低填写门槛）且精度公认最优；蛋白按体重是健身场景科学做法；增减可覆盖兼顾默认与个性化 | Harris-Benedict（老、偏高5%）、Katch-McArdle（需体脂率，users 无此字段）；宏量按纯百分比（不贴合个体） |
| 2026-06-18 | N2：身体数据存 users 表（5 列 nullable）；营养目标独立 user_nutrition_goals 表（user_id UUID FK→users CASCADE unique）；is_custom 标记手动覆盖 | 身体数据是用户属性归 users，目标是算出的独立实体可扩历史；user_id 必须 UUID 对齐真实 users.id（非 ERD 草图 BIGINT） | 全塞 users 表（目标无法扩历史）、user_id 用 BIGINT（与 UUID 主键不匹配连不上） |
| 2026-06-18 | N3：营养目标算一次存库（非实时算） | 用户可手动覆盖，覆盖值必须存（实时算会冲掉自定义）；目标不常变无需每次重算；同 D6 缓存思想 | 每次请求实时算（冲掉用户自定义、且无谓重算） |
| 2026-06-18 | N4：身体数据与算目标分两步（PUT body-metrics / POST nutrition-goal/compute）；4 端点挂 /users/me 带认证；upsert on user_id（一人一条目标） | 分步让用户先填身体数据再选目标，改身体数据不无脑覆盖已自定义目标；认证照常用 get_current_user | 一步提交（耦合）、加 dev 后门绕认证（增加临时代码） |
| 2026-06-19 | P1/P2：meal_plans + meal_plan_entries 照 ERD；user_id 用 UUID；entry 三 FK 差异化（meal_plan_id CASCADE、recipe_variant_id RESTRICT）；不直接存 user_id（经 plan 间接关联） | 计划是容器、餐次依附计划走 CASCADE；排进计划的菜谱版本受保护走 RESTRICT（同 recipe_ingredient 护共享资源）；归属在 plan 层，entry 无需 UUID FK | entry 直挂 user（削弱多计划能力）、recipe_variant CASCADE（删菜谱悄悄清空计划） |
| 2026-06-19 | P2-a/P2-b：同餐次不防重复（靠 sort_order 排多道菜）；加 entry 校验日期在 plan 范围内（超范围 422，default plan 除外） | 一餐多道菜是常态不该约束；显式计划日期越界是脏数据该拦；DB CHECK(end≥start) 兜底 | 唯一约束防重复（早餐吃两样就挂）、不校验日期（脏数据） |
| 2026-06-19 | P3/P4：daily-summary 按 user+date 跨所有 plan 汇总 vs 目标；NULL 传播到达标率；单计划操作做归属校验（非本人 → 404 不泄漏存在性） | 记录型用户餐在 default plan、规划型在显式 plan，「今天吃了啥」须跨 plan；404 而非 403 防 plan id 枚举；NULL 传播延续 D2 避免未知伪装成 0 | 按单 plan 汇总（漏跨 plan 的餐）、403（泄漏存在性）、NULL 当 0（误导达标率） |
| 2026-06-19 | 选 2：quick-log 端点 + default plan（get-or-create）+ 动态撑大范围，服务记录型用户无感记录；显式建计划服务规划型用户 | 识别规划型 vs 记录型两种用户心智，MVP 同时服务；MealPlan 灵活日期范围（单日/多日/重叠）无需改结构即支持两者 | 只做显式计划（挡记录型用户）、重构 entry 直挂 user（削弱规划能力、大改结构） |

---

## 修订记录

### 2026-07-23（Week 5 实现时对 D 系列的修订）

以下 Week 1-2 设计期决策在实现中调整。**原条目保留**以显示演进过程。

**1. "库存记 `shortage_grams` 字段" → 短缺不落库**

改为仅在 API 响应中返回短缺列表（见 I1）。
理由：短缺是瞬时计算结果；落库会与 Week 6 采购缺口（I7）形成两个真相源，重复计算易漂移。

**2. "Snapshot + Event Log 双写架构" → 状态表 + append-only 审计流水**

措辞修正（见 I2）。关键差异：**当前库存不由事件求和得出**，`inventory_items` 是唯一真相源，
`inventory_transactions` 纯审计。因此流水可设 90 天保留期而不影响库存正确性 ——
纯事件溯源无法随意截断历史（截断即算错当前值）。

**3. "`quantity_grams` CHECK ≥ 0" → 建表时遗漏，已补 ✅**

2026-07-23 补上，约束名 `ck_inventory_items_qty_non_negative`（migration `7ce8329404eb`）。
非负性现有**双层保护**：应用层 FEFO 的 `min()` + DB 层 CHECK 兜底。
面试点：关键不变量应在 DB 层用约束固化，不只依赖应用层逻辑。

**4. "`inventory_transactions` 双时间戳（occurred_at + created_at）" → 建表时只做了 occurred_at，已补 ✅**

2026-07-23 补上 `created_at`（migration `e43bb8446f56`）。
两者分开的意义：支持用户事后补录（"中午做的饭刚想起来记"），
时间点回放需按 `occurred_at`（事件发生时间）切片，而非 `created_at`（DB 写入时间）。

**5. ERD 中 inventory 两表的字段级差异 → 已同步 ✅**

`docs/ERD.md` 第 11/12 节已于 2026-07-23 重写为实际实现
（UUID、DATE、`input_amount`/`input_unit`、`location`、CHECK 约束、FEFO 三级排序、
`reason`/`source_entry_id`、去掉 `shortage_grams`/`transaction_type`/`related_meal_log_id`）。
架构原则第 3 条措辞修正；Decision 2 / Decision 6 保留原文并追加修订说明。

---

## I 系列 — 库存与采购决策（Week 5+）

> 编号说明：I5、I12 为讨论中合并/取消的条目，编号保留不复用，避免历史引用失效。

### I1 — `inventory_items` 批次模型 ✅ 已实现

- **批次模型**：一食材可多行（按批次），无唯一约束
- **扣减顺序（FEFO）**：`expires_at ASC NULLS LAST, purchased_at ASC NULLS LAST, id ASC`
  - 先过期先扣；平手或都为空则先买先扣（FIFO）
  - **`id ASC` 是必需的确定性兜底**：前两个键可空且可重复，无法保证全序；
    缺它会导致同过期日批次的扣减顺序不确定（同样输入两次跑结果不同）
- **库存下限**：扣到 0 为止，不下穿负数（`SUM` 恒 ≥ 0，语义 = "实际持有"）
  - DB 层 `CHECK (quantity_grams >= 0)` 固化此不变量（2026-07-23 补）
- **短缺处理**：不足部分作为独立信号返回，**不写回库存表**
- **主键**：`BigInteger`（对齐既有业务表约定；仅 `users.id` 为 UUID）
- **`user_id`**：UUID FK → `users.id`（清 Week 2 的 BIGINT 类型债）
- **可空**：`expires_at` / `purchased_at`（类型为 `DATE`，非 TIMESTAMPTZ）
- **`location`**（`VARCHAR(20)` 可空，值域 `fridge` / `freezer` / `pantry`，2026-07-23 加）
  - **加它的理由（用户视角）**：同一食材冷冻可放 3 个月、冷藏 2 天 ——
    **存放位置改变保质期语义**；且取用时需知道是否要提前解冻
  - 与批次模型天然契合：1kg 肉一半冷藏一半冷冻 = 两个批次，`expires_at` 与 `location` 都不同
  - 未来可长出：按 location 建议默认 `expires_at`（选冷冻 → +90 天）、
    "明天计划用冷冻食材 → 今晚解冻"提醒、库存按位置分组显示
  - **`notes` 不实现**：用户不会填，填了也不驱动任何行为
    （典型的"看似有用、实际无人用"字段）
- **索引**：`(user_id, ingredient_id, expires_at)`
- **零余量批次保留**（不删除）：撤销完成餐次时可直接 `+= take` 回补，
  批次元数据（过期日/入库日）尚在；删除则无法重建。查询需 `WHERE quantity_grams > 0` 过滤。
  空间代价可忽略（约 150 字节/行，重度用户 1000 行/年 ≈ 150 KB）

**补充（2026-07-23）：`input_amount` 是入库快照，不可修改**

- `input_amount` / `input_unit` = 入库时的原始输入（D5=B 双表示，展示用），**仅 POST 写入**
- `quantity_grams` = 当前余量，可被 FEFO 扣减与 PATCH 盘点修改
- **PATCH 只改 `quantity_grams`**
  - 用户视角：库存界面改数字意为"我现在还剩多少"，不是"我当初买了多少"
  - 入库历史应保持不变，否则记录失真（扣过的批次会把已消耗量凭空变回来）
- 盘点值允许为 0（`ge=0`，"吃完了"）；入库必须 > 0（`gt=0`）
- **已知局限**：PATCH 无法把日期字段主动清空回 NULL
  （JSON 的 `null` 与"未传"在 Python 中均为 `None`，无法区分）。
  需要时可用 Pydantic `model_fields_set` 区分。

### I2 — 扣减机制：状态表 + append-only 流水 ✅ 已实现

- `inventory_items` = **当前库存真相源**（读路径 O(1)，不聚合事件）
- `inventory_transactions` = append-only 审计流水
  （`delta_grams` / `reason` / `inventory_item_id` / `source_entry_id` / `occurred_at` / `created_at`）
- **`occurred_at` vs `created_at` 分开**（2026-07-23 补）：
  前者是事件发生时间、后者是 DB 写入时间。支持事后补录，
  时间点回放按 `occurred_at` 切片才正确
- **保留策略**：流水只留近 90 天（可配），到期清理**不影响当前库存**
  —— 这是相对纯事件溯源的关键优势（审计日志有独立生命周期）
- **撤销完成餐次**：追加反向流水 + 回补 `inventory_items`
- **FK 语义**：`inventory_item_id` / `source_entry_id` 均 `ON DELETE SET NULL`
  —— 批次或餐次被删，审计记录保留，仅指针置空
- **并发安全**：取批次时用 `SELECT ... FOR UPDATE`（`with_for_update()`）加行锁，
  防两个请求同时完成餐次导致重复扣同一批次
- **事务边界**：service 内只 `flush`，`commit` 由 router 统一执行 ——
  使"标记完成 + 扣库存 + 记流水"三表在单一事务内原子提交
- **幂等**：`complete_entry` 遇 `is_completed=True` 直接返回，不重复扣减

**补充（2026-07-23）：流水只记系统性消耗**

- **记流水**：`purchase`（入库）、`meal_consumption`（做饭扣减）
- **不记流水**：PATCH 盘点修正、DELETE 删批次
- **理由（用户视角）**：用户查流水是想追溯"食材被哪顿饭消耗了"，
  不关心自己手动修正的历史。人工调整属于"修正记录本身"，不是消耗事件。
- 代价：手动改动无审计痕迹 —— 接受（单用户场景，无合规需求）
- `reason` 枚举中 `'adjustment'` / `'waste'` 保留字段值，暂不使用

### I3 — 单位：克本位地基 → 多单位换算 🚧 分期

**Week 5 已实现：克本位地基**

- 库存 `quantity_grams` 一律存基准单位（g / ml）
- 菜谱需求、扣减、入库全部在基准单位下运算
- 输入即克（`input_unit` 暂为 `'g'`，`quantity_grams = input_amount`）

**Week 6+ 叠加：换算层**

- 用 `ingredients.grams_per_unit`（Week 2 已建）实现"2 个洋葱 → 克"
- 用户可改换算率默认值；用户可自定义单位

**设计要点**：换算隔离在 I/O 边界，核心库存逻辑永远在克本位下运行
—— 加换算不动核心，只在"用户输入"与"内部存储"间插一层翻译。

### I4 — 临期提醒 ✅ 已实现

- **单级黄色**：`expires_at` 在未来 N 天内
  （N 默认 3，`settings.inventory_expiry_warning_days` 可配）
- **已过期也算 `'expiring'`**（`days_left <= N`，负数自然满足）；
  未来若需区分可加 `'expired'` 值（字段预留、值渐进）
- **查询时计算，不落库** —— `status = f(expires_at, now)` 是时间的函数，
  落库就要跟时钟赛跑刷新；派生值随输入变化时，存储是负债不是优化
- **`expires_at IS NULL` 永不提醒**（显式排除）

### I6 — 库存预扣视图 ⏳ Week 6

- **实际库存**（存储，非负）+ **预计剩余**（实时算，**可负**）
- 预计剩余 = 实际库存 − 范围内未完成 entry 的食材需求
- **负数是核心信号**：`洋葱 -200g` = "排的饭会缺 200g" → 驱动采购
  （这是"短缺可见"需求的正确归宿：让预测为负，而非让实际库存为负）
- **预测视界**：默认 7 天（一个采购周期），支持自定义范围 / 全量
  —— 纯全量会把三周后的计划算进来，导致现在囤货、囤了会坏
- **绝不真扣库存**：预扣是读时计算的视图，不落库。
  否则计划一改就要反向回补，且"还没做的饭"凭什么扣真实库存

### I7 — 缺口统一计算 ✅ Week 6 实现

- 单一函数 `compute_shortfall(user, start_date, end_date)`
  = Σ（范围内未完成 entry 的食材需求）− 现有库存 SUM
- **一函数多呈现**：库存视图显示为"预计剩余（负）"；采购清单显示为"待购（正）"
- **范围参数各自可传**，默认值共享（7 天）
  —— 计算逻辑共用避免数值漂移；但库存视图是探索性范围、采购是决策性范围，不锁同一值
- 面试点：single source of computation，避免两处各算一遍导致不一致

### I8 — 采购清单双来源 ✅ Week 6 实现

- `auto`：由 I7 缺口生成，随计划/库存**重算**
- `manual`：用户手动添加，重算时**保留不覆盖**
- 两者隔离 —— 否则重算一次会把用户手动加的项冲掉

### I9 — 采购回流库存 ✅ Week 6 实现

- 填"实际购买量" → `inventory_items` 新增批次 + `purchase` 流水
- 新批次 `expires_at` 默认 NULL（按 I4 不提醒），之后可在库存界面补填
- 购买单位 ↔ 库存单位换算依赖 I3 的换算层
- 可顺带填 `location`（决定默认保质期建议）

### I10 — 采购项属性 ✅ Week 6 实现

- `add_to_inventory: bool` —— 厨房纸等非食材 = `false`（纯提醒，买完打勾即完）
- 与 I8 的 `source`（auto/manual）**正交**，两个独立维度
- `manual` 项可为纯文本，**不必关联 `ingredient_id`**（非食材不进 ingredients 表）
- 添加物品的交互：选已有食材 / 创建新食材（填营养）/ 创建非食材（纯文本）

### I11 — 用户自建内容（ingredient / recipe / variant）⏳ Week 6

**Week 6 实现：私有创建**

- `created_by_user_id`：`BigInteger` → 改 **UUID + FK → users.id**（清 Week 2 的类型债）
- 新增 `visibility` 字段：`'private'`（默认）/ `'global'`
  —— **独立于 `source`**：`source` 是"哪来的"（usda/system/user），`visibility` 是"谁能看"
- 查询过滤：用户只见「自己私有的 + `visibility='global'` 的」
- `ingredients` 已有 `source='user'` 可复用；recipe / variant 同加两字段

**愿景，暂不实现（记录设计意图）**

- 申请转全局：`private → pending_review → global / rejected` 状态机
  （可直接扩展 `visibility` 的值域，不需改表 —— 字段预留、值渐进）
- 审核工作流：审核者角色、审核队列、批准/驳回（附理由）
- **判断**：UGC 内容治理属平台成熟期功能。单人开发无法验证"提交者 vs 审核员"两方流程，
  投入产出比低于库存一致性等核心能力。MVP 只做私有创建，预留字段与路径。

### I13 — `entry.servings` = 配方倍数 ✅ 语义定案

- **`entry.servings` = 做且吃的配方倍数**（`0.25` = 只做了 1/4 个配方）
- **扣减 = `RecipeIngredient.quantity_grams × entry.servings`**（不除 `variant.servings`）
- **与 Week 4 营养聚合一致**：`daily-summary` 用 `variant.total_calories × entry.servings`，
  同样不除 —— 同一字段必须同一语义，否则营养与扣减会各算一套
  （这是发现该语义的关键：若扣减除以 `variant.servings` 而营养不除，同一个 entry
  会算出"吃了两锅的热量、用了半锅的料"）
- **`variant.servings` = 纯展示**（"每份热量" = `total ÷ servings`），**不参与任何计算**

**已知缺口：批量烹饪 / 剩菜**

- 物理现实：做整锅消耗整锅原料；若分几顿吃，系统按"吃的倍数"扣减会低估原料消耗
- **正确解（未实现）**：双层库存 —— `cook` 动作扣整锅原料 + 增成品库存；
  `eat` 动作扣成品份数。需新增成品实体、成品保质期（熟食远短于生食）、营养换算
- **判断**：批量烹饪与剩菜管理是独立子系统（Phase 3+）。
  主流场景"做一份吃一份"下当前模型准确，不为边缘场景引入双层库存复杂度
- 备选方案 B（完成时扣整锅）已否决：同一锅分 2 顿吃会重复扣两次整锅，比当前偏差更大
- 命名 smell：字段名 `servings` 实为"倍数"，略误导；改名需 migration，暂不动，以本条说明语义

---

## 技术债

| # | 债务 | 来源 | 状态 |
| --- | --- | --- | --- |
| 1 | ~~`inventory_items.quantity_grams` 缺 `CHECK >= 0`~~ | 修订 3 | ✅ 2026-07-23（`7ce8329404eb`） |
| 2 | ~~`inventory_transactions` 缺 `created_at`（补录时间错位）~~ | 修订 4 | ✅ 2026-07-23（`e43bb8446f56`） |
| 3 | ~~ERD 第 11/12 节与实现约 10 处字段级不一致~~ | 修订 5 | ✅ 2026-07-23 已同步 |
| 4 | ERD 中 Phase 2 表（shopping / notes / meal_logs）`user_id` 仍为 BIGINT 草图 | Week 2 defer | ⏳ 做到那张表时校准 |
| 5 | `ingredients.created_by_user_id` 类型不匹配（BigInteger vs UUID） | Week 2 defer | ⏳ Week 6（I11 需要） |
| 6 | 零余量批次与 90 天前流水的定期清理任务 | I2 | ⏳ Week 7（引入后台任务时） |
| 7 | `quick-log` 返回的 entry 不含 `meal_plan_id`，无法直接 complete | Week 5 测试发现 | ⏳ 低（Week 10 前端时补） |
| 8 | ~~`location` / `notes` 未实现~~ | Week 5 | ✅ 2026-07-23 定案：`location` 已加，`notes` 不做 |

---

## 流程笔记

### Alembic migration 验证清单（本项目踩过三次的坑）

1. **`--autogenerate` 不检测 CheckConstraint 增删** → 这类约束必须手写 migration
   （加列 / 加表能检测；约束、索引名变更、CHECK 不行）
2. **`alembic upgrade` 输出没有 `Running upgrade X -> Y` 那行 = 什么都没执行**
   - 空 migration（model 未被 `alembic/env.py` import）会静默"成功"
   - 版本已记录为 applied 时，改文件内容也**不会**重跑
3. **apply 前先 `grep -A8 "def upgrade" <文件>`** 确认里面不是 `pass`
4. 版本记录与实际库状态不一致时用 **`alembic stamp <rev>`** 修正指针（不执行 DDL）；
   不要用 `downgrade`（会尝试 DROP 不存在的对象而报错）
5. 加约束前先查现有数据是否满足（`SELECT COUNT(*) WHERE <违反条件>` 应为 0）
6. 删 migration 文件前先看 `alembic current`：在 current 之后可直接删；
   是/早于 current 必须先 downgrade，否则 `alembic_version` 指向不存在的 revision
7. 新建域后记得在 `alembic/env.py` 加 `from app.<domain> import models  # noqa: F401`，
   否则 model 不进 `Base.metadata`，autogenerate 检测不到

### 其他易踩点

- **FastAPI 路由顺序敏感**：静态路径（`/daily-summary`）必须注册在动态路径（`/{plan_id}`）之前，
  否则被捕获为参数并返回 422，且**不会** fallthrough 到后面的路由
- **`lru_cache` 缓存的 settings**：改 `.env` 后需完全重启进程，`--reload` 不一定生效
- **"假 CORS"**：后端 500 时无法附加 CORS 响应头，浏览器报的 CORS 是表象，
  真因要看后端 Traceback
- **`localhost` ≠ `127.0.0.1`**：origin 层面是不同源，同时影响 CORS 白名单与 Clerk `azp`，
  两处都须与浏览器地址栏一致
- **排序必须全序**：可空/可重复的排序键需补唯一列（如 `id`）兜底，否则结果不确定
  —— 这类 bug 时对时错，测试极难发现
- **中文标点混入代码**：全角顿号 `、` 等会导致 `SyntaxError: invalid character`，
  粘贴后扫一眼行尾
- **测试脚本不要硬编码会被删除的 id**：应在脚本内先创建再操作，保证可重复运行