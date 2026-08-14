# MealForge 设计决策记录

> 本文件是所有架构决策的**唯一记录处**（single source of truth）。
> 记录内容：决策本身、理由、备选方案，以及后续实现中的**修订**。
> 决策编号：`D` = 环境与架构（Week 1-4，含 D/N/P 系列），`I` = 库存与采购（Week 5+），
> `AI` / `R` / `P` / `F` = AI 生成 / 菜谱内容 / 性能缓存 / 前端，`DEP` = 部署（Week 11）。
> 设计在实现中演进是正常的 —— 修订会保留原条目并标注，不做无痕修改。

## 目录

- [D 系列 — 环境与架构决策（Week 1-4）](#d-系列--环境与架构决策week-1-4)
- [修订记录](#修订记录)
- [I 系列 — 库存与采购决策（Week 5+）](#i-系列--库存与采购决策week-5)
- [AI 系列 — AI 生成决策（Week 7+）](#ai-系列--ai-生成决策week-7)
- [R 系列 — 菜谱内容决策](#r-系列--菜谱内容决策)
- [P 系列 — 性能与缓存决策（Week 9）](#p-系列--性能与缓存决策week-9)
- [技术债](#技术债)
- [流程笔记](#流程笔记)
- [F 系列 — 前端决策(Week 10)](#f-系列--前端决策week-10)
- [DEP 系列 — 部署决策（Week 11）](#dep-系列--部署决策week-11)

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

### I6 — 库存预扣视图 ✅ Week 6 实现

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

### I11 — 用户自建内容（ingredient / recipe）✅ Week 6 实现（MVP）

**Week 6 MVP：仅私有创建 + 可见性过滤**

- `created_by_user_id`：`BigInteger` → 改 **UUID + FK → users.id**（清 Week 2 的类型债 #5）
- 新增 `visibility` 字段：`'private'`（默认）/ `'global'`
  —— **独立于 `source`**：`source` 是"哪来的"（usda/system/user），`visibility` 是"谁能看"
- 查询过滤：用户只见「自己私有的 + `visibility='global'` 的」
  → `WHERE visibility='global' OR created_by_user_id = <me>`
- 加在 **ingredient + recipe 两级**（不加 variant）：variant 可见性天然继承其 recipe，
  现实无独立控制需求
- **决策 A：`recipes.is_public` 收敛进 `visibility`**（True→global / False→private），删 is_public，
  统一一个概念，与 ingredient 一致
- 数据回填：现有 USDA 食材、系统菜谱是共享参考数据 → `visibility='global'`
  （否则加完字段默认 private，用户看不见已有食材，直接崩）

**明确不在本次 MVP（依赖尚不存在的"公开菜谱"功能，记录设计意图）**

以下三层均依赖"公开菜谱浏览/分享"流程（当前 `is_public` 只是字段，无真正公开流程），
待做 UGC / 公开分享迭代（Week 8+ 或专门迭代）时统一设计：

1. **公开菜谱"带出"其引用的私有食材**（核心修正，否则公开菜谱会坏）：
   菜谱一旦 global，其引用的私有食材必须对查看者**可读**（显示名/算营养），但标注"私人创建"。
   → 食材可见性不能只看自身行，需考虑"是否被某个 global 菜谱引用"（JOIN 引用关系）。
   → 这推翻了纯内容级 `WHERE visibility='global'` 的简单规则。
2. **私有食材申请转公开**：`private → pending_review → global / rejected` 状态机
   （直接扩展 `visibility` 值域，不需改表 —— 字段预留、值渐进）+ 审核工作流
3. **公开时 AI/搜索去重**：用户公开菜谱时，AI 对比私有食材与现有公开食材库
   （或用户搜索公开食材），提示"保留私有版 or 替换为公开版"，避免重复建"腐乳"

- **判断**：第 1 层依赖公开菜谱功能；第 2/3 层属平台成熟期（审核治理 + AI 去重）。
  单人开发 MVP 只做私有创建 + 过滤，预留 `visibility` 值域与演进路径。

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

## AI 系列 — AI 生成决策（Week 7+）

### D-AI1 — AI 菜谱生成：grounding + 结构化输出 ✅ Week 7 实现

- **场景（第一版）**：从用户库存生成菜谱（"我冰箱里这些能做啥"）
- **grounding（防幻觉，核心）**：把用户库存食材清单（id + 名字）喂进 prompt，
  要求 AI 只能用清单内的 `ingredient_id` 引用，不得自造食材
  → **软约束（prompt）+ 硬校验（代码 `_validate` 逐个 id 查是否在清单内）双层防幻觉**
  → 即便 AI 幻觉出清单外 id，代码拦截、判失败、不写脏数据
- **结构化输出**：用 tool use / function calling（`save_recipe` 工具，schema = 菜谱结构），
  强制 AI 按结构返回，避免解析自由文本的脆弱性
- **输入方式**：结构化选项（免费，前端拼 prompt）+ 一句自由文本（便宜）+ **单次生成**
  → 不做多轮聊天（省 token）；食材清单**限量**（库存 or 精选常用，只给 id/name 省 input token）
- **落库**：`source='ai_generated'`、`visibility='private'`、归属当前用户；复用 recipe 创建逻辑
  + `compute_variant_nutrition` 聚合营养（不信 AI 自报营养）

### D-AI2 — 失败也记日志 + 两段事务 ✅ Week 7 实现

- `ai_generation_logs` 表：user/kind/status/model/prompt/raw_response/token(输入输出分开)/
  error_message/created_recipe_id/created_at。`kind` 预留 meal_plan（Week 8 复用）
- **成功/失败都记**：失败的调用最需要留痕（debug 幻觉/超时/模型下线）
- **事务策略**：校验先于持久化 → 失败时尚未建任何菜谱行 → 无需回滚，只独立提交 failed 日志；
  成功时菜谱 + 日志同事务提交，两向 FK 互链（recipe.ai_generation_log_id ↔ log.created_recipe_id）
- **价值实证**：真出 502 时（模型下线），error_message 精确记下 404 原因，一眼定位

### D-AI3 — 供应商：Anthropic → Gemini，adapter 层可切换 ✅ Week 7 实现

- **选型**：起步 Anthropic（tool use 强），后因成本改用 **Google Gemini 免费层**
  （永久免费、Flash-Lite 1000 次/天，够 MVP + 30-50 用户）
- **⚠️ Gemini 坑**：一旦开启 billing，该项目免费层立即消失（每 token 计费）；配额可能被砍；
  免费层数据用于改进 Google 产品（菜谱不敏感，可接受）
- **adapter 层实证**：从 Anthropic 切到 Gemini **只改 `app/ai/client.py` 一个文件 + 配置**，
  `services.py`/端点/49 个测试**零改动全过** → LLM 供应商可插拔，业务不锁定单一厂商
- **模型串号配置化**：`GEMINI_MODEL` 放 settings/.env。`gemini-2.5-flash` 对新用户下线返 404，
  改 `.env` 一行换 `gemini-3.1-flash-lite` 即修复 → **模型会下线，串号绝不硬编码**

### D-AI4 — AI 周计划：从已有菜谱排布 ✅ Week 8 实现

- **第一版**：AI 从用户【可见菜谱的做法(variant)】里挑选, 排布成 N 天计划(默认 7 天午晚餐)
  —— 不生成新菜谱(生成 Week 7 已会, 后续叠加)
- **grounding**：喂"可用做法清单(variant_id + 菜名 + 主料)", AI 只能挑清单内 variant;
  `_validate_plan` 硬校验 variant_id 在清单内 + day_offset 合法 + meal_type 合法(三重防幻觉)
- **落库**：复用 meal_plans/meal_plan_entries, plan_type='ai_generated';
  `ai_generation_logs.kind='meal_plan'`(Week 7 预留字段用上);meal_plans.ai_generation_log_id 补 FK
- **client 泛化**：抽通用 `_call_tool`, recipe 生成与 plan 生成共用调用核 —— 加新 AI 功能
  只需新 tool schema + 瘦包装, 不改调用逻辑(开闭原则)
- **愿景**：第二版"已有不足时 AI 生成新菜谱补齐"(catalog 不够时调 generate_recipe, 主流程不变)

### D-AI-愿景 — 生成来源演进（暂不实现，记录意图）

食材清单来源可替换，主流程（拼 prompt→调 AI→校验→落库→记日志）不变：

1. **第一版（已实现）**：从库存生成 —— grounding=库存
2. **第二版**：从库存 + 全库按要求选 —— grounding=更大清单（换"取清单"那一步）
3. **第三版**：网络/知识热门菜谱 —— 放开 grounding + AI 联网 + I11(c) 自动建私有食材
   （突破"只能用给定食材"前提，与 I11 公开菜谱愿景勾连）

## R 系列 — 菜谱内容决策

### D-R1 — 反向推荐：纯查询 + 宽松匹配 ✅ Week 8 实现

- **纯查询, 不用 AI**：库存能做哪些【已有可见菜谱做法】= 集合运算(菜谱所需食材 ⊆ 库存)
  —— 与 Week 7 "AI 从库存现编" 互补(一个找现成的, 一个 AI 编新的)
- **variant 级**：配料挂在 variant 上, 推的是"某菜谱的某做法", 最准
- **宽松匹配**：缺 ≤max_missing(默认 2)也推荐并列出缺啥; 缺太多过滤; 按缺料数升序
- **只看有没有(不看克数)**：第一版按食材种类匹配, 精确到克留进阶
- **无 N+1**：库存集合 1 查 + JOIN 拉全菜谱配料 1 查 + 内存聚合(对齐 compute_shortfall)
- `GET /recipes/recommendations?max_missing=2`(注册在 /{recipe_id} 前避免路由遮蔽)

### D-R2 — 菜谱同名策略：允许同名(A) + 引导用 variant(D, 暂不实现)

- **决策 A：允许同名**。菜谱天然会重名(每家的番茄炒蛋), 强行唯一(唯一约束)或
  自动改名("(2)" 后缀)都别扭 —— 菜谱是内容不是文件, 系统擅自改名体验差
- **"同一道菜的不同做法" = 同一菜谱的多个 variant**, 不是建两个菜谱(模型本意)
- **愿景 D(暂不实现, 记录意图)**：创建菜谱时若检测到同名, 提示用户
  "给现有菜谱『X』加一个新做法(variant), 还是确实建一个独立新菜谱?" —— 引导用 variant
- **关联**：与 I11 "AI 去重"、D-AI 愿景同类(内容去重/引导), 依赖创建流程交互提示,
  属产品成熟期
- **当前**：不拦截同名; recommend_recipes 如实推荐(recipe_id 不同即不同菜谱)
- **注**：现有两条同名 "Chicken rice bowl"(id 1/2)是 Week 2 测试误建的重复数据, 已清理

## P 系列 — 性能与缓存决策（Week 9）

### D-P1 — 每日营养汇总缓存：Cache-Aside + Redis ✅ Week 9 实现

- **问题**：`GET /daily-summary` 每次请求都聚合(查当天所有餐次 + 各 variant 营养 ×
  份数 + 查目标)。同一天数据不变时重复算是浪费, 用户多/数据大时成为热点。
- **Cache-Aside(旁路缓存)**：先查 Redis, 命中直接返回; 未命中才聚合, 算完写回 Redis。
  业务逻辑零改动, 只在端点头尾包一层。
- **key 设计**：`summary:{user_id}:{date}` —— 带 user_id(隔离+隐私)、date(按天)。
  **存与删用同一个 `summary_key()` 生成**, 避免拼错对不上删不掉。
- **TTL 兜底**：默认 1 小时过期 —— 即便主动失效漏了某处, 最坏也只旧 1 小时。

### D-P2 — 缓存失效策略：写操作精准失效 ✅ Week 9 实现

- **原则**：任何改变"某天营养"的写操作, 成功后主动删对应天的缓存 key, 下次请求重算。
- **覆盖的 6 个写操作 → 失效的天**：
  - quick-log / add-entry / complete-entry → 那餐的 `scheduled_date`(单天)
  - delete-entry → 被删餐日期(**删前记录**, 删后取不到)
  - generate(AI 周计划) / delete-plan → 计划覆盖的每一天(`_dates_in` 展开; delete 删前记范围)
- **难点(记录, 第一版未做)**：改一道 variant 的配料/营养 → 它被排进的**所有天**缓存都该失效,
  需反查"该 variant 被哪些天用了"。当前 variant 营养改动少 + TTL 兜底, 暂缓; 是下一步优化点。

### D-P3 — 优雅降级：缓存永不拖垮业务 ✅ Week 9 实现

- **Redis 是可丢的加速副本, 真相在 Postgres**。故 `cache.py` 所有操作 try/except 兜底:
  get 出错当未命中(退回查库)、set/delete 出错静默忽略。
- **效果**：Redis 挂了 → daily-summary 仍 200(退回聚合), 写操作仍成功(只是没删成缓存)。
  缓存是锦上添花, 绝不因它引入新崩溃点。

### D-P4 — 附带修复：路由遮蔽(FastAPI 静态 vs 动态) ✅ Week 9

- **bug**：`GET /daily-summary` 返回 422 "unable to parse 'daily-summary' as integer"
  —— 被先注册的 `GET /{plan_id}` 当成 plan_id。之前无数据未测到, 加缓存时才暴露。
- **修**：`/{plan_id}` → `/{plan_id:int}`(动态路由只匹配整数)+ 静态路径前置。双保险。
- **教训**：静态路由永远放动态路由前; 路径参数能加类型约束就加, 比纯靠顺序健壮。

### 测试(fakeredis, 不依赖真容器)

- 用 `fakeredis` + FastAPI `dependency_overrides[get_redis]` 注入假 redis(同 mock Gemini 思路)。
- 6 个测试: 路由不遮蔽 / 未命中存缓存 / 命中读缓存 / 写失效 / 失效后重算 / Redis 挂了降级。
- `cache_redis` fixture 暴露 api_client 用的同一假 redis 供断言; api_client 返回值不变(不破坏旧测试)。

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
| 9 | ~~Python 版本未锁定（`.python-version` 缺失 → 本地 3.14.5 / CI 3.12 长期漂移）~~ | Week 1 | ✅ 2026-08-13（DEP0） |
| 10 | ~~`.env.example` 缺 4 个 config 项（CORS 一项 + Gemini 三项）~~ | Week 7、Week 10 | ✅ 2026-08-13（DEP8） |
| 11 | `create_async_engine` 无 `connect_args`，接 Neon 需加 `statement_cache_size=0` | DEP3 | ⏳ Week 11 Step 2 |
| 12 | 全仓 lint 欠账（CI 仅覆盖 shopping/ingredients/recipes/ai/meal_plans/tests） | Week 7+ | ⏳ 低 |
| 13 | 缓存失效第二版：variant 营养变更 → 反查受影响天精准失效 | D-P2 | ⏳ 低（TTL 兜底中） |

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


---

## F 系列 — 前端决策(Week 10)

### D-F1 — 技术栈:React+Vite+纯JS + Tailwind+shadcn/ui ✅ Week 10
- **纯 JS 不上 TS**:降复杂度,作品集重点是全栈闭环非类型体操。
- **shadcn/ui(复制源码模式)**:组件源码进项目 = 拥有代码可改;AI 生成友好;业界主流。
- **不用 shadcn Select,用原生 `<select>`**:简单可靠,少配置。
- 坑:`DialogTrigger asChild` 内必须用 `<span role="button">` 不用 `<button>`(否则 button 套 button)。

### D-F2 — api 统一封装 + useApi hook ✅ Week 10
- 所有请求走 `lib/api.js`(base URL + JSON + token + ApiError)。页面不直接 fetch。
- `useApi().call(apiFn, path, opts)` 自动从 Clerk 取 token 注入。
- `extractDetail`:FastAPI 错误 detail 可能是数组/对象,统一提成可读字符串(避免 `[object Object]`)。
- api 方法:get/post/put/patch/del(put 曾漏,body-metrics 需要)。

### D-F3 — 库存三区渐变(方案B) ✅ Week 10
- location(pantry/fridge/freezer)→ 三竖区,响应式 grid 3→2→1 列(竖排堆叠不横滑)。
- 卡片背景按剩余天数连续渐变:0天红→14天绿(HSL hue 0→120),无过期日中性灰排最后。
- **不加"调料区"**:分区维度是存储温度,混入食材类型会破坏一致性;需冷藏的调料归冷藏区。
- **未指定区**:location 为 null/其他的落这里(采购回流未选区的);卡片可编辑改区归位。
- 过期标签前端算(daysUntil<0=已过期红/≤3天=临期橙),不依赖后端 expiry_status(它只有临期无过期)。

### D-F4 — 加库存两步式 + 库存编辑 ✅ Week 10
- 加:视图1 选食材(后端 `?name=` 前缀搜索 + visibility 分"我的/公共" + 搜不到可创建)→ 视图2 填详情。弹窗内两视图切换(step state),不做整页路由。防抖 useDebounce 300ms。
- 编辑:卡片点击 → PATCH /inventory/{id} 改数量(盘点,可为0)/过期日/区域。

### D-F5 — 餐计划多视图 + 多plan ✅ Week 10 / 月视图 backlog
- 视图:天(竖)+ 周(横/竖),共 4 种。切换器两个开关 [天|周][竖|横](横竖仅周视图)。月视图不做。
- 架构预留:viewMode state / 数据层(/entries 按范围取)与视图解耦 / MealEntryCard 复用 / dateRange 工具。加月视图=加渲染分支,不碰数据。
- 多 plan 层次C:默认合并显示所有 plan + PlanBar 可筛选单个。plan 只填 name(description 需改 model+迁移,记 backlog),日期用今天+排餐自动扩展。删除 plan 移到选中后右上角红按钮(防误触)。
- AI 生成建新 plan;手动排餐用 `POST /{plan_id}/entries` 选 plan(非 quick-log)。

### D-F6 — 采购结算流程 ✅ Week 10
- 清单项 = 勾选 + 输入买入量(非逐个"买了")。底部一次性"结算"。
- 结算弹窗:勾选项列出,每样分配储存区(默认冷藏)+ 可填过期日 → 逐个 purchase 回流(前端组织批量,后端逐项端点)。
- 后端 purchase 加 location/expires_at 透传 → 回流批次直接归区带过期日(修复原"回流无 location 落未指定区")。
- 缺口预览项可"加入清单"(可调量,默认缺口量)。

### D-F7 — 营养目标页 ✅ Week 10
- 流程:PUT /users/me/body-metrics(存身体数据)→ POST /users/me/nutrition-goal/compute(算 TDEE,身体数据没填齐后端 422)。
- **端点前缀提醒**:nutrition router prefix = `/users/me`(非 `/nutrition`);shopping = `/shopping-lists`(非 `/shopping`)。前端拼路径前务必确认后端 prefix。

---

## DEP 系列 — 部署决策（Week 11）

> 目标：把 MealForge 部署上线，产出面试可用的公网链接。
> 编号 DEP0–DEP8，按"准备 → 平台 → 数据层 → 前端 → 认证 → 运维"顺序排列。

### DEP0 — Python 版本收敛：双层约束锁定 3.12 ✅ 2026-08-13

**审计发现（部署前环境一致性检查，与预期不符）**

原以为的问题是"`.python-version` 锁了 3.14，改成 3.12 即可"。读代码后发现实情不同：

1. **`.python-version` 从未存在**（`.gitignore` 中也未排除）。
   `pyproject.toml` 写的是 `requires-python = ">=3.12"`，只有下界没有上界，
   uv 遂挑选系统上可用的最新版本 —— 3.14.5。
   **问题不是"锁错了版本"，而是"根本没锁"**，因此修复方式是补上缺失的约束而非改一个值。
2. **CI 一直硬编码 `uv python install 3.12`**。
   即：**本地跑 3.14.5、CI 跑 3.12，已漂移数周而未被察觉**。
3. **`uv.lock` 因上界开放而生成两套 resolution-markers**
   （`python_full_version >= '3.14'` 与 `< '3.14'`）。实测：

   | 指标 | 数量 |
   | --- | --- |
   | cp312 wheel 条目 | 137 |
   | **cp314 wheel 条目** | **280** |

   含 3.14 专属 wheel 的 14 个包全是 C 扩展依赖：
   `asyncpg` / `cffi` / `charset-normalizer` / `coverage` / `cryptography` /
   `greenlet` / `httptools` / `markupsafe` / `pydantic-core` / `pyyaml` /
   `sqlalchemy` / `uvloop` / `watchfiles` / `websockets`
   —— **asyncpg、pydantic-core、sqlalchemy、cryptography 正是数据层与认证层的地基**，
   本地与 CI 装的是不同的编译产物。

**为什么它一直没炸**：这些依赖在两个版本上行为恰好一致，且 CI 长期绿灯，
间接提供了"代码能在 3.12 上运行"的证据。**但这是运气，不是设计。**

**决策：双层约束，两处都做**

| 机制 | 管什么 | 单独使用的漏洞 |
| --- | --- | --- |
| `.python-version` = `3.12` | uv 本地建 venv 用哪个解释器 | **不影响依赖解析**，lock 中 3.14 分支仍在 |
| `requires-python = ">=3.12,<3.13"` | uv 解析依赖时考虑哪些版本 | 不指定具体版本，uv 仍需别处得知装哪个 |

**这与 `quantity_grams` 的处理同构**：应用层 FEFO `min()` + DB 层 `CHECK >= 0` 双重保障。
关键不变量在两层固化，不依赖单点或人为约定。

**配套：CI 改为读 `.python-version`**

`uv python install 3.12` → `uv python install`（不带参数，自动读文件）。
版本号在全仓只剩一个来源，消除"改了本地忘了 CI"这一漂移成因
—— 同 `summary_key()` 统一生成缓存 key、`line_demand` 抽单一真相源的思路。
同时新增 `uv run python -V` 步骤，让实际版本在 CI 日志中可见，使未来漂移显性化而非隐形。

**为什么是 3.12 而非 3.13**

部署阶段的首要指标是**可重现性**，不是版本新。
3.12 生态最成熟，全部 C 扩展依赖均有预编译 wheel，`python:3.12-slim` 官方镜像稳定；
3.13 的 free-threading 仍在铺开，部分 wheel 覆盖不完整。
用新版本换来的性能提升在本项目负载下测不出来，换来的构建失败风险却是实打实的。

**验收标准（可量化，优于"测试绿了"）**

```
grep -c cp314 uv.lock    # 重建前 280 → 重建后应为 0
```

依赖树真正收敛到单一版本的硬证据。

**改动面（四处）**：新建 `.python-version` / `pyproject.toml` 加上界 /
删除并重建 `uv.lock` / CI 改为读文件。

**备选**：留在 3.14（部分库需现场编译，`google-genai` 已报 DeprecationWarning）；
升到 3.13（生态仍在追赶）；只建 `.python-version` 不加上界（lock 仍双分支，治标不治本）。

### DEP1 — 后端平台：Fly.io

- Docker 原生（本项目已容器化）、region 可选（需与 Neon 对齐）、CLI 体验好、按秒计费。
- **备选**：Railway（更简单但免费额度收紧）、Render（冷启动更慢）、
  自建 VPS（运维面过大，单人项目承担不起）。

### DEP2 — 对象存储：本周不做，推迟 ⏸

- **理由：项目当前没有任何文件上传功能**（菜谱图片在 Brief 中列出但从未实现）。
  为不存在的功能选型是过度设计，违背既定的"演进式设计，推迟复杂度"原则。
- **若将来做则选 Cloudflare R2**：零 egress 费（图片读多写少，egress 是主要成本）；
  S3 兼容 API 意味着迁回 S3 只改 endpoint，供应商锁定风险低。
- **面试点**：能说清"为什么现在不做"和"做的话怎么选"，
  比硬塞一个用不上的集成更有说服力。

### DEP3 — 数据库：Neon Free（非 Fly Postgres）

- **选定 Neon Free**：$0，0.5 GB 存储 + 100 CU-hours/月，scale-to-zero。
  本项目数据量（USDA 食材子集 + 用户数据）远低于上限。
- **备选一 Fly Managed Postgres**：$38/月起 —— 作品集场景成本不合理。
- **备选二 Fly 非托管 Postgres**：约 $2–7/月，但官方已标 legacy 且明确不提供支持，
  备份 / 版本升级 / 灾备全部自理 —— 单人项目承担不起这个运维面。
- **代价（必须处理）**：
  1. scale-to-zero 冷启动 300–500 ms。
  2. **pooled 连接走 PgBouncer 事务模式，不支持 prepared statements**；
     asyncpg 默认开 statement cache，需在 `app/core/database.py` 的
     `create_async_engine` 加 `connect_args={"statement_cache_size": 0}`，
     否则报 `prepared statement "__asyncpg_stmt_N__" does not exist`。
     **当前该调用无 `connect_args`（只有 `echo` 与 `pool_pre_ping`），Step 2 需修改。**
  3. Neon region 需与 Fly app region 对齐，否则每次查询多几十毫秒，
     `daily-summary` 这类多查询端点会被放大。

### DEP4 — 前端托管：Cloudflare Pages

- 免费 + 全球 CDN + push 自动构建；首屏速度直接影响招聘官第一印象。
- **备选**：在 Fly 上起第二个 app 反代 `/api` 做同源（可彻底消灭 CORS/azp 配置），
  但多一台机器成本 + nginx 配置；而 CORS 本项目 Week 5 已调通，不构成新增成本。
- **必须配 SPA fallback 到 `index.html`** —— react-router 是客户端路由，
  否则用户直接访问 `/recipes/12` 会 404。
- **注意**：`VITE_API_BASE_URL` 是 **build-time** 注入（字面替换进 bundle），
  非运行时读取。后端域名变更必须重新 build 重新部署，改环境变量无效。

### DEP5 — Clerk：分两阶段切换，不与首次部署同时进行

- **阶段一（Step 0–10）**：沿用 dev instance + 免费域名（`*.fly.dev` / `*.pages.dev`），
  先把部署链路整体跑通。
- **阶段二（Step 11）**：买域名 → 开 Clerk production instance → 切 issuer / key / azp。
- **理由：一次只改一个变量**。首次部署时新变量已有 5 个
  （镜像 / Neon 连接 / Upstash / CORS / 前端域名），
  若同时更换认证（issuer 变、JWKS 变、key 变、用户库清空），
  登录返回 401 时无法定位是哪一层。
  参照 Week 5 的"假 CORS"教训 —— 表象与真因分离的问题必须靠隔离变量排查。
- **待验证前提**：dev instance 是否允许非 localhost origin。
  须在 Step 6 之前于 Clerk Dashboard 确认；
  若不允许，则 Step 11 需提前至 Step 6，域名要提早购买。

### DEP6 — 迁移执行：Fly `release_command` 自动 `alembic upgrade head`

- 保证代码与 schema 永远同步，不会出现"代码上线了但表没建"。
- **代价**：坏迁移会阻断整次部署；失败不会自动 downgrade。
- **缓解**：沿用既有 Alembic 验证清单（apply 前 `grep -A8 "def upgrade"` 确认非 `pass`；
  确认输出含 `Running upgrade X -> Y` 那行），
  并保留 `fly ssh console` 手动跑迁移的兜底路径。

### DEP7 — 后端常驻：`min_machines_running = 1`，不启用 scale-to-zero

- 省下的几美元 < 招聘官点开链接白屏 8 秒、误以为项目已挂的损失。
- **这是面向真实用户（招聘官）的决策，不是纯技术最优解** ——
  与项目一贯的"先从真实用户视角推理"原则一致。

### DEP8 — `.env.example` 补齐为部署配置清单 ✅ 2026-08-13

审计发现 4 个配置项在 `app/core/config.py` 中存在但 `.env.example` 未记录：
`CORS_ALLOWED_ORIGINS_RAW` / `GEMINI_API_KEY` / `GEMINI_MODEL` / `AI_MAX_TOKENS`。

**为何是部署阻塞项而非洁癖**：`.env.example` 是"线上必须配哪些变量"的唯一清单，
灌 `fly secrets` 时照它执行。缺项导致的两种失效**都不会在启动时报错**：

- `gemini_api_key` 有默认空值 → 服务正常启动，用户点"AI 生成"时才炸
- `cors_allowed_origins_raw` 有 localhost 默认值 → 服务正常启动，前端全部请求被浏览器拦

**启动即失败远优于运行时静默失效** —— 这类"只在用户操作时暴露"的配置缺失最难排查。
补齐时按"本地专用 / 部署需改"分组，并就地标注两条既有教训：
`localhost` ≠ `127.0.0.1`（CORS 与 azp 两处都敏感）、模型串号必须可配置（模型会下线）。

### Week 11 部署顺序（执行清单）

| # | 步骤 | 完成标志 |
| --- | --- | --- |
| 0 | Python 3.12 收敛（DEP0）+ `.env.example` 补齐（DEP8） | `grep -c cp314 uv.lock` = 0；93 测试全绿；CI 绿 |
| 1 | Dockerfile 多阶段构建，本地连本地 PG/Redis 跑通 | 容器内 `/health` 与 `/docs` 可访问 |
| 2 | Neon 建库；加 `statement_cache_size=0`；从本地 `alembic upgrade head` | `\dt` 看到全部表 |
| 3 | **灌 seed 数据到生产库**（USDA 食材） | 线上库食材表非空 |
| 4 | Upstash 建 Redis，本地用线上 `REDIS_URL` 验证 | daily-summary 命中缓存 |
| 5 | `fly launch` + `fly secrets set` + deploy | 公网 `/health` 返回 200 |
| 6 | 前端 build + 部署 Pages | 页面可打开（此时 API 因 CORS 失败属正常） |
| 7 | 回填 CORS + azp，后端重新 deploy | 登录打通 |
| 8 | 端到端冒烟：登录→加库存→AI生成→排餐→扣库存→采购→回流→概览 | 全链路走通 |
| 9 | CD：push main → 自动 deploy | push 后线上自动更新 |
| 10 | Sentry + README + demo 账号 | 招聘官点开即可看 |
| 11 | 买域名 + Clerk production instance（DEP5 阶段二） | 自定义域名 + prod key 下登录正常 |

**易漏点**：第 3 步（线上空库会让反向推荐 / AI / 采购全部失效）；
第 8 步 Gemini 免费层有速率限制，连测多次可能撞 429，需确认错误提示可读；
第 10 步招聘官不会注册账号，必须准备 demo 账号或演示 GIF。

### Week 11 待采集的简历数据

- `uv.lock` 中 cp314 条目 **280 → 0**（依赖树收敛的量化证据，已采集）
- Docker 镜像体积：**单阶段 vs 多阶段**（Step 1 必须先构建单阶段版本量一次，否则无对照组）
- 线上 `daily-summary` 缓存命中 vs 未命中的 p50/p95 延迟
- Neon scale-to-zero 唤醒实测耗时
- 月总成本（"一个全栈 + AI 的生产应用，$X/月"—— 成本意识是面试加分项）
- **优雅降级实证**：切断 Redis 后 API 仍返回 200 的线上日志（D-P3 的真实环境验证）
- CI/CD 时长：`git push` 到线上生效的秒数
