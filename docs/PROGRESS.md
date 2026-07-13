# MealForge 开发进度

> 这个文件追踪项目实际开发进度。每完成一个 chat 任务后更新。
> Claude 在新 chat 开始时应先读这个文件，了解当前状态。

---

## 🎯 当前状态

- **当前周次**：Week 4 完成 ✅ —— Phase 1（MVP 基础）收官，准备进「Clerk 前端骨架」里程碑
- **当前任务**：Week 4 餐食规划全部完成。MealPlan/MealPlanEntry 两表 + 计划 CRUD + quick-log（default plan 无感记录）+ daily-summary（跨 plan 汇总 vs 目标）。前三周（食材/菜谱/营养目标）由 daily-summary 真正串起来。
- **上次更新**：2026-06-19
- **下一步**：Clerk 前端骨架里程碑（见 docs/FRONTEND_MILESTONE.md）—— 打通登录+真 token，一次性真测积压的认证端点（/users/me + 营养目标 4 个 + 计划全家桶）

### Week 5 — 库存管理（决策已定，待实现）
- 决策 I1–I10 锁定（详见 CHANGELOG）
- Week 5 实现范围：inventory_items + inventory_transactions 建表/migration、
  user_id UUID 校准、库存 CRUD、FEFO 扣减挂 MealPlanEntry.complete、临期提醒、克本位
- I6–I10（预扣视图/缺口函数/采购）实现推迟到 Week 6

### 项目基础信息

- **GitHub Repo**: https://github.com/junhao-logan/mealforge
- **本地路径**: `/home/junhao_logan/projects/mealforge/`
- **本次新增**: app/users/{models,schemas,router}.py、app/auth/{**init**,dependencies}.py、alembic/versions/911b07ee6f47_create_users_table.py
- **本次改动**: app/core/config.py、app/main.py、alembic/env.py、.env(.example)
- **依赖新增**: pyjwt[crypto]
- **commit**: `feat(users): add User model and initial migration`（已提交）；auth 代码建议补一个 `feat(auth): Clerk JWT verification + /users/me`（hash 待填）

### 待办（晚于主线，需要时再做）

- ⬜ 在 WSL 装 Claude Code CLI (`npm install -g @anthropic-ai/claude-code`)
- ⬜ 验证 VS Code Claude Code 扩展连上 WSL 里的 CLI
- ⬜ Windows 上的旧 Node (D:\nodeJs\) 暂时被屏蔽，需要时清理
- ⬜ 加 `.python-version` 锁定 Python 版本（uv 默认抓了 3.14.5，太新；Week 11 部署前需确认 Railway/Fly 运行环境版本对齐）

---

## 📅 12 周进度概览

- [x] **Week 1**: 设计与搭建（ERD ✅、骨架 ✅、认证 ✅；README v1 待补）
- [x] **Week 2**: 菜谱与食材模块（食材层 USDA seed + 查询 API；菜谱层 Recipe/Variant/Ingredient 三表 + CRUD + 营养聚合，全部跑通）
- [~] **Week 3**: 营养目标与 TDEE（TDEE 计算 ✅ + 营养目标 CRUD ✅；每日营养汇总挪到 Week 4，依赖餐计划数据）
- [x] **Week 4**: 餐食规划 v1（MealPlan/Entry + 计划 CRUD + quick-log + 每日营养汇总；**里程碑：自己可用 ✅ Phase 1 收官**）
- [ ] **Week 5**: 库存管理
- [ ] **Week 6**: 智能采购清单
- [ ] **Week 7**: AI 菜谱生成
- [ ] **Week 8**: AI 周计划 + 反向推荐（**里程碑：核心闭环完成**）
- [ ] **Week 9**: 测试与性能优化
- [ ] **Week 10**: 前端打磨
- [ ] **Week 11**: 部署上线
- [ ] **Week 12**: 推广与迭代（**里程碑：30-50 真实用户**）

---

## ✅ 已完成事项

> 格式：每周一个小节，按时间倒序记录。

### Week 1 ✅

- [x] 数据库 ERD 设计（15 张表，7 个核心设计决策的 trade-off 文档化）
- [x] FastAPI 项目骨架（domain-driven）
- [x] Docker Compose（PostgreSQL + Redis）
- [x] Alembic 初始化（async env.py）
- [x] Alembic 第一份 migration（待 users 表确定后生成）
- [x] 用户认证集成
- [x] README v1

---

## 🧭 关键技术决策记录

> 每个重要选择都记下"为什么"，将来面试讲得出来。

| 日期       | 决策                                                                                                                                                                                       | 理由                                                                                                                                                                                                                                   | 备选方案                                                                                                                                |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-05-13 | 开发环境选 Windows + WSL2/Ubuntu 22.04                                                                                                                                                     | 部署目标是 Linux，本地用 Linux 保证一致性；避开 Windows 上 uvloop 等库的兼容问题                                                                                                                                                       | 纯 Windows、Mac、Linux 双系统                                                                                                           |
| 2026-05-13 | Python 工具链选 uv                                                                                                                                                                         | Rust 实现速度快 10-100 倍、统一替代 pip/poetry/pyenv/virtualenv、海外新项目主流                                                                                                                                                        | pipenv（维护乏力）、poetry（更新慢）、pip+venv（手动管理累）                                                                            |
| 2026-05-13 | Node 通过 nvm 安装而非 apt                                                                                                                                                                 | apt 源里的 Node 版本过老（12.x，已 EOL）；nvm 支持多版本切换便于回退                                                                                                                                                                   | apt install、NodeSource 源、fnm                                                                                                         |
| 2026-05-13 | 用 Node 24 LTS                                                                                                                                                                             | 当前最新 LTS（Active LTS 阶段），30 个月支持周期                                                                                                                                                                                       | Node 22（前一代 LTS）、Node 20（更稳）                                                                                                  |
| 2026-05-13 | Docker 用 Docker Desktop + WSL Integration，不在 Ubuntu 独立装                                                                                                                             | 一次配置 Windows/WSL 共用 Engine；Docker Desktop 个人用户免费；管理方便                                                                                                                                                                | WSL 里独立 apt install docker.io                                                                                                        |
| 2026-05-13 | 代码放 `/home/junhao_logan/`，不放 `/mnt/d/`                                                                                                                                               | WSL 原生文件系统比挂载的 Windows 盘快 10 倍，npm install/docker build/git 都受益                                                                                                                                                       | 放 D 盘方便 Windows 端访问                                                                                                              |
| 2026-05-13 | 项目目录用 `~/projects/mealforge`                                                                                                                                                          | `~/projects` 集中放所有项目，符合行业惯例；不放 `/mnt/d` 避免文件系统慢 10 倍                                                                                                                                                          | 直接放家目录、放 D 盘                                                                                                                   |
| 2026-05-13 | GitHub 仓库选 Monorepo（前后端同仓）                                                                                                                                                       | 个人项目前后端强耦合；招聘官点一个链接看全部；docker-compose 统一启动                                                                                                                                                                  | 双仓库分离                                                                                                                              |
| 2026-05-13 | 用 SSH key 而非 HTTPS + PAT 跟 GitHub 通信                                                                                                                                                 | 配一次永久无密码；私钥不外传比 PAT 安全；服务器运维必备技能                                                                                                                                                                            | HTTPS + Personal Access Token                                                                                                           |
| 2026-05-13 | SSH key 算法选 ed25519                                                                                                                                                                     | 2014 后的最佳选择，短、快、安全；GitHub 推荐                                                                                                                                                                                           | RSA 4096（兼容性更好但更长）                                                                                                            |
| 2026-05-13 | SSH key 不设 passphrase                                                                                                                                                                    | 个人开发机物理被偷概率低；git 操作完全无感更顺                                                                                                                                                                                         | 设 passphrase + ssh-agent 缓存                                                                                                          |
| 2026-05-13 | Conventional Commits 规范（feat:/fix:/chore: 等）从第一个 commit 开始用                                                                                                                    | commit history 像产品、未来可自动生成 CHANGELOG                                                                                                                                                                                        | 自由格式 commit message                                                                                                                 |
| 2026-05-13 | 项目骨架走"最小起步"路线，不一次性建完整目录                                                                                                                                               | commit history 看着像"持续工作"而非一次性堆完；学习曲线更平缓；每步都能跑                                                                                                                                                              | 一次性建完整 Monorepo 结构                                                                                                              |
| 2026-05-13 | README 用纯文字 + 粗体，不用 badges                                                                                                                                                        | 干净专业，避免"入门项目堆 badges"的廉价观感                                                                                                                                                                                            | 满屏 badges                                                                                                                             |
| 2026-05-13 | License 选 MIT                                                                                                                                                                             | 最宽松最常见，海外项目标配；不影响商用未来扩展                                                                                                                                                                                         | Apache 2.0、GPL                                                                                                                         |
| 2026-05-19 | 食材份量统一存克数，UI 单位元数据下放到 Ingredient 表                                                                                                                                      | 营养计算 O(1) 算术；与 USDA per-100g 数据天然对齐；用户输入体验不损失（default_unit + grams_per_unit）；跨菜谱营养汇总简单                                                                                                             | 在 RecipeIngredient 上存原始单位 + UnitConversion 表（N+1 查询噩梦）                                                                    |
| 2026-05-19 | 库存采用 Snapshot + Event Log 双写架构                                                                                                                                                     | 读路径 O(1)，事件流支持时间点回放、消耗趋势、临期预测；对账机制可检测漂移；是真实生产系统常见做法                                                                                                                                      | 纯 CRUD 覆写 quantity（丢历史）、纯事件溯源（读慢）                                                                                     |
| 2026-05-19 | 库存不足不阻断，记 shortage_grams 字段；inventory_items.quantity_grams CHECK ≥ 0                                                                                                           | 用户体验流畅；自动喂入"急需采购"建议；语义清晰（库存永远 ≥ 0）                                                                                                                                                                         | 允许 quantity 为负（语义怪）、硬阻断（用户体验差）                                                                                      |
| 2026-05-19 | MealPlan 任意起止日期 + 允许重叠 + plan_type 字段                                                                                                                                          | 支持任意周期（周/月/5 天冲刺）；模板和实际计划可并存；用户灵活分类                                                                                                                                                                     | 固定周一到周日（不够灵活）、DB 强制不重叠（用户难用）                                                                                   |
| 2026-05-19 | Recipe → RecipeVariant 两级抽象，食材挂 Variant                                                                                                                                            | 一个菜可有多种做法（经典/减脂/增肌）；AI 可生成"已有菜谱的减脂变体"；产品体验更好                                                                                                                                                      | 单层 Recipe + parent_recipe_id 软关联（搜索体验差）                                                                                     |
| 2026-05-19 | purpose_tag 固定枚举 + recipe_variant_tags 自由标签的双层混合                                                                                                                              | 核心分类强约束（保证 AI 理解、筛选、统计）；个性化标签完全自由；产品和用户决策权分明                                                                                                                                                   | 完全自由文本（拼写漂移污染筛选）、纯固定枚举（用户表达力受限）                                                                          |
| 2026-05-19 | 营养信息缓存到 recipe_variants 表 + 同步/异步混合 invalidation                                                                                                                             | 读路径零计算；21 餐 × 5 食材的周聚合从 100+ JOIN 降到 21 次直接读；nutrition_computed_at 兜底排查                                                                                                                                      | 实时算（每次 JOIN，N+1 风险）                                                                                                           |
| 2026-05-19 | AI 调用独立 ai_generation_logs 表，prompt_input_hash 作缓存键                                                                                                                              | 支撑限流、prompt A/B、输出缓存（预期节省 60% LLM 成本）、成本看板、失败率监控                                                                                                                                                          | 把 AI 字段直接挂到 Recipe 表（数据混乱、无法分析）                                                                                      |
| 2026-05-19 | inventory_transactions 同时记 occurred_at（事件发生）和 created_at（DB 写入）                                                                                                              | 支持用户事后补录（"我中午做的饭刚想起来记一下"），时间点回放查询走 occurred_at 才正确                                                                                                                                                  | 只记 created_at（补录数据会错位）                                                                                                       |
| 2026-05-19 | meal_logs 暂不建表，MVP 用 meal_plan_entries.is_completed 替代                                                                                                                             | 减少 Week 1-4 实现负担；等真用起来观察用户偏离计划的模式再演化；演进式设计本身是简历故事                                                                                                                                               | Week 1 就建 meal_logs 表（前 4 周用不上）                                                                                               |
| 2026-05-19 | notes.rating 是 1-10 主观评分，语义由用户自定义                                                                                                                                            | 不强加单一维度（好吃 / 难度 / 满意度由用户决定）；产品决策权下放                                                                                                                                                                       | 固定"好吃程度 5 分制"（限制用户）                                                                                                       |
| 2026-05-30 | 目录结构走 domain-driven（按领域：core/health/...，后续 auth/recipes/inventory/ai）                                                                                                        | 10+ 领域模块按层划分会很乱；相关代码同目录、重构友好；fastapi-best-practices 推荐；面试叙事更专业                                                                                                                                      | layered（按层：api/models/schemas/services）                                                                                            |
| 2026-05-30 | ORM 用 async（asyncpg + AsyncSession + SQLAlchemy 2.0）                                                                                                                                    | 与 FastAPI async-first 一致；后续 AI 调用是多秒级 I/O，async 让 worker 等待时处理别的请求；海外 SDE 基础要求                                                                                                                           | sync（psycopg2 + Session，需 run_in_threadpool 包一层）                                                                                 |
| 2026-05-30 | 依赖管理用 pyproject.toml + uv（PEP 621），app 以 hatchling editable 装入 venv                                                                                                             | 海外主流、uv 原生支持；editable 安装保证 import app 不受 cwd/sys.path 影响                                                                                                                                                             | requirements.txt、uv workspace                                                                                                          |
| 2026-05-30 | Alembic 走 async 模板，单一 asyncpg driver                                                                                                                                                 | 全栈只用一个 driver，不必为迁移装 psycopg2、不维护两套连接串；代价是 env.py 略复杂（一次性）                                                                                                                                           | 同步迁移（psycopg2，双 driver）                                                                                                         |
| 2026-05-30 | Base.metadata 挂 naming_convention（ix/uq/ck/fk/pk）                                                                                                                                       | 约束名确定可读，autogenerate diff 干净、downgrade 能精准点到约束名；15 张表建完再补是迁移灾难                                                                                                                                          | 用 SQLAlchemy 默认隐式约束名                                                                                                            |
| 2026-06-02 | 认证用托管 Clerk 而非自撸 JWT                                                                                                                                                              | 自撸 auth（密码哈希/重置/邮箱验证/OAuth/session 撤销/防爆破）高风险低回报、面试不加分；精力留给 AI + 库存差异化；免费 50k MAU                                                                                                          | 自撸 JWT（fastapi-users / 纯手写）、Auth0                                                                                               |
| 2026-06-02 | Clerk over Supabase Auth                                                                                                                                                                   | 栈已 commit 自托管 Postgres + SQLAlchemy + Alembic；Supabase Auth 的 RLS 红利（auth.users 与业务表同库）用不上、反成 split-brain；Clerk 是独立身份层，契合现状                                                                         | Supabase Auth                                                                                                                           |
| 2026-06-02 | users 表用 identity shadow（业务 FK 指 internal UUID，非 Clerk ID）                                                                                                                        | 第三方身份与本地领域用户解耦；换 provider 只重映射影子表一列，业务表不动；clerk_user_id 作锚点                                                                                                                                         | 直接拿 Clerk user id 当 PK（provider 锁定）                                                                                             |
| 2026-06-02 | JIT user provisioning（webhook 延后）                                                                                                                                                      | 首鉴权请求 upsert 影子行，免 webhook 投递可靠性/乱序/本地隧道；删除同步等需要时再补 user.deleted webhook（演进式设计）                                                                                                                 | 启动即 webhook 全量同步                                                                                                                 |
| 2026-06-02 | networkless JWT 验证（JWKS 公钥本地验签 + 缓存）                                                                                                                                           | 延迟低、避开 API 限流；自己用 PyJWT 验 iss/azp/exp，面试能讲清原理；run_in_threadpool 不堵事件循环                                                                                                                                     | 每请求调 Clerk authenticate API、SDK 黑盒验                                                                                             |
| 2026-06-02 | per-domain 增量 migration（非一次性建 15 表）                                                                                                                                              | ERD 是蓝图、按域逐步物化；migration history 可 review、像持续工作；避免一堆空表                                                                                                                                                        | big-bang 一次建完 15 表                                                                                                                 |
| 2026-06-02 | clerk_user_id 仅 unique 不加 index                                                                                                                                                         | Postgres 唯一约束自带索引，再加 index 造成重复索引                                                                                                                                                                                     | 额外 index=True                                                                                                                         |
| 2026-06-02 | dev 阶段 azp 校验留空跳过                                                                                                                                                                  | 无前端时用裸 token/Backend API 测、azp 来源不固定；接前端后填 origin 再启用                                                                                                                                                            | dev 即强制 azp                                                                                                                          |
| 2026-06-16 | USDA 子集 = Foundation Foods 2025-12 + SR Legacy 精选；CSV 快照、版本钉死、不走实时 API；精选 200–400 条通用食材                                                                           | seed 是一次性可复现离线动作，CSV 快照保证确定性+无网络耦合+无限流；Foundation 新质量高但覆盖窄、SR Legacy 广但 2018 冻结，二者互补；精选子集搜索干净、seed 快、可扩                                                                    | 实时 API（运行时耦合网络+限流）、全量 7800 条（稀释搜索）、含 Branded（百万级噪声污染搜索）                                             |
| 2026-06-16 | 营养锁四宏量 kcal/protein/fat/carb，numeric nullable，不设非 NULL 默认值；energy 取值优先级 1008→2048→2047 单位锁 kcal                                                                     | 0 ≠ unknown，NULL 才能表达"无数据"（避免给控钠/控糖用户错误信息）；USDA 一条食材可能多行 energy（SR 用 1008、Foundation 常见 Atwater 2047/2048），定确定性优先级保证跨数据集一致；幂等 seed 让延迟加列零成本                           | 全字段 NOT NULL（语义错）、默认值填 0（把 unknown 谎报成 0）、一次性全加 100+ 营养素（列爆炸）                                          |
| 2026-06-16 | seed 走独立幂等脚本（非 Alembic data migration），usda_fdc_id 作 upsert key（ON CONFLICT DO UPDATE）；人工单位字段与 USDA 营养字段分离更新                                                 | schema migration 只管结构、不背批量参考数据；fdc_id 全球唯一稳定，重跑安全；分离更新避免重灌冲掉手工裁决的 default_unit/grams_per_unit                                                                                                 | 把 seed 塞进 data migration（文件臃肿、downgrade 删数据语义乱）、name 作 key（不稳定）                                                  |
| 2026-06-16 | grams_per_unit 用单列 NUMERIC（方案 a），每食材一个非克单位 + 克兜底；手工填 + foodPortions 机会性参考；多单位等 Phase 2 unit_options 表                                                   | MVP 真实需求是"每食材一个好用单位 + 克兜底"（鸡蛋→个、米→杯、肉→克），单列够用；foodPortions 脏（modifier 自由文本）不盲信，精选子集让人工裁决可行；JSONB 多单位会增加 D7 查询复杂度且提前打乱 ERD 演进                                | 现在上 JSONB 多单位（过早抽象）、全量 import foodPortions（脏数据污染单位下拉）、UnitConversion 表（ERD 已否决，N+1）                   |
| 2026-06-16 | USDA 子集 = Foundation Foods **2026-04-30** + SR Legacy 2018-04 精选；CSV 快照、版本钉死、不走实时 API；精选 200–400 条通用食材                                                            | （理由同前）实际下载版本为 2026-04-30（锁决策后 USDA 又发新版），版本号以硬盘真实快照为准                                                                                                                                              | （同前）                                                                                                                                |
| 2026-06-16 | 原始 USDA CSV gitignored，不进 commit；可复现性靠「决策表记录的发布版本 + manifest 里的 fdc_id」双重兜底                                                                                   | fdc_id 全局稳定（D3），即便重下新版，manifest 的 fdc_id 仍解析到同一批食材，仅营养数值可能微调；原始 CSV 体积大、不宜入库                                                                                                              | 把原始 CSV 也 commit（仓库臃肿）、纯靠版本号（CSV 不在库无法核对）                                                                      |
| 2026-06-16 | seed upsert（S4）= 方案 a 全刷：ON CONFLICT DO UPDATE 同时刷营养 4 列 + 单位 4 列（name/category/default_unit/grams_per_unit）                                                             | manifest + USDA 快照是唯一 SoT，"改 manifest→重跑→DB 同步"心智模型最简；D3 设想的"人工/营养分离"在 manifest 架构下已天然实现（单位来自 committed manifest、营养来自 CSV，物理分离），无需 SQL 层再分离；MVP 无"用户编辑 seed 食材"功能 | 方案 b 只刷营养（单位冻结，改 manifest 不生效）、方案 c 全刷+WHERE source='usda' 守卫（防用户改动被冲，但防的是不存在的风险，过早抽象） |
| 2026-06-17 | D5：RecipeIngredient 存份量 = 方案 B（归一化 quantity_grams + 用户原始 input_amount/input_unit 双存）；写入时换算（input_amount × grams_per_unit），单位限 default_unit 或克（D5a）        | 克数供 O(1) 营养聚合、与 USDA per-100g 对齐；同存原始输入供友好显示（"2 个"而非"100g"）；单位约束直接由 D4"单 default_unit + 克兜底"推导，不引入多单位换算表                                                                           | 方案 A 只存克（丢显示语义）、方案 C 只存原始单位（读时现算，N+1，ERD 已否决）                                                           |
| 2026-06-17 | D6：营养聚合 = 独立 service（compute*variant_nutrition）+ 配料变动时同步算 + 缓存回写 RecipeVariant（total*\* + nutrition_computed_at）；NULL 传播为"不完整"不当 0；异步批量重算留 Phase 2 | 配料就几条，同步聚合毫秒级，无需异步；NULL 传播延续 D2 的 0≠unknown 到聚合层，避免 unknown 误当 0 误导用户；异步价值在 Phase 2 食材更新批量重算场景                                                                                    | 一上来就上异步（过早）、NULL 当 0 加（语义错）                                                                                          |
| 2026-06-17 | D7：读取份量直接显示 input_amount/input_unit，quantity_grams 仅供计算                                                                                                                      | D5=B 的自然结果——写时换算一次、读时零换算；memory 里"换算查询时机"顾虑就此消解                                                                                                                                                         | 读时反算（多余）、ERD 原稿方案 A 无原始单位可显示                                                                                       |
| 2026-06-18 | N1：BMR 用 Mifflin-St Jeor；活动系数标准 5 档；目标热量 TDEE±默认增减（减脂−500/维持0/增肌+400）可由 calorie_delta 覆盖；宏量蛋白按体重 2g/kg + 脂肪 25% 热量 + 碳水填余                   | Mifflin-St Jeor 不需体脂率（降低填写门槛）且精度公认最优；蛋白按体重是健身场景科学做法；增减可覆盖兼顾默认与个性化                                                                                                                     | Harris-Benedict（老、偏高5%）、Katch-McArdle（需体脂率，users 无此字段）；宏量按纯百分比（不贴合个体）                                  |
| 2026-06-18 | N2：身体数据存 users 表（5 列 nullable）；营养目标独立 user_nutrition_goals 表（user_id UUID FK→users CASCADE unique）；is_custom 标记手动覆盖                                             | 身体数据是用户属性归 users，目标是算出的独立实体可扩历史；user_id 必须 UUID 对齐真实 users.id（非 ERD 草图 BIGINT）                                                                                                                    | 全塞 users 表（目标无法扩历史）、user_id 用 BIGINT（与 UUID 主键不匹配连不上）                                                          |
| 2026-06-18 | N3：营养目标算一次存库（非实时算）                                                                                                                                                         | 用户可手动覆盖，覆盖值必须存（实时算会冲掉自定义）；目标不常变无需每次重算；同 D6 缓存思想                                                                                                                                             | 每次请求实时算（冲掉用户自定义、且无谓重算）                                                                                            |
| 2026-06-18 | N4：身体数据与算目标分两步（PUT body-metrics / POST nutrition-goal/compute）；4 端点挂 /users/me 带认证；upsert on user_id（一人一条目标）                                                 | 分步让用户先填身体数据再选目标，改身体数据不无脑覆盖已自定义目标；认证照常用 get_current_user                                                                                                                                          | 一步提交（耦合）、加 dev 后门绕认证（增加临时代码）                                                                                     |
| 2026-06-19 | P1/P2：meal_plans + meal_plan_entries 照 ERD；user_id 用 UUID；entry 三 FK 差异化（meal_plan_id CASCADE、recipe_variant_id RESTRICT）；不直接存 user_id（经 plan 间接关联）                | 计划是容器、餐次依附计划走 CASCADE；排进计划的菜谱版本受保护走 RESTRICT（同 recipe_ingredient 护共享资源）；归属在 plan 层，entry 无需 UUID FK                                                                                         | entry 直挂 user（削弱多计划能力）、recipe_variant CASCADE（删菜谱悄悄清空计划）                                                         |
| 2026-06-19 | P2-a/P2-b：同餐次不防重复（靠 sort_order 排多道菜）；加 entry 校验日期在 plan 范围内（超范围 422，default plan 除外）                                                                      | 一餐多道菜是常态不该约束；显式计划日期越界是脏数据该拦；DB CHECK(end≥start) 兜底                                                                                                                                                       | 唯一约束防重复（早餐吃两样就挂）、不校验日期（脏数据）                                                                                  |
| 2026-06-19 | P3/P4：daily-summary 按 user+date 跨所有 plan 汇总 vs 目标；NULL 传播到达标率；单计划操作做归属校验（非本人 → 404 不泄漏存在性）                                                           | 记录型用户餐在 default plan、规划型在显式 plan，「今天吃了啥」须跨 plan；404 而非 403 防 plan id 枚举；NULL 传播延续 D2 避免未知伪装成 0                                                                                               | 按单 plan 汇总（漏跨 plan 的餐）、403（泄漏存在性）、NULL 当 0（误导达标率）                                                            |
| 2026-06-19 | 选 2：quick-log 端点 + default plan（get-or-create）+ 动态撑大范围，服务记录型用户无感记录；显式建计划服务规划型用户                                                                       | 识别规划型 vs 记录型两种用户心智，MVP 同时服务；MealPlan 灵活日期范围（单日/多日/重叠）无需改结构即支持两者                                                                                                                            | 只做显式计划（挡记录型用户）、重构 entry 直挂 user（削弱规划能力、大改结构）                                                            |

---

## 🔧 选料规则（填 manifest 时遵守）

1. grep `food.csv` 永远叠 data_type 过滤：只认 `"foundation_food"` / `"sr_legacy_food"`，跳过 `market_acquisition`/`sample_food`/`sub_sample_food`（那些是溯源样本，非成品）
2. 认 **raw**（生重），不选 cooked/braised（用户买生食材、按生重下厨）
3. 同名两数据集都有成品 → 优先 Foundation（新、质量高）
4. `name` 写干净显示名，不抄 USDA 原串

---

## ❓ 待解决问题 / 技术债务

> 遇到没解决的问题先记着，别卡住主线。

- [ ] 液体食材按 g≈ml 近似存储（油密度 0.92，未来用户抱怨精度再加 Ingredient.density 字段）
- [ ] 食材搜索 MVP 用 LIKE 'xxx%'，Phase 2 视用户反馈考虑 pg_trgm 模糊搜索
- [ ] 食材别名（番茄 / 西红柿）暂不做，等用户反馈"搜不到"再加 ingredient_aliases 表
- [ ] 多语言菜谱字段（name_i18n JSONB）暂不做
- [ ] notes.rating 多维度评分（好吃 / 难度 / 性价比 / 健康）暂不做，等用户反馈
- [ ] Python 版本未锁定（uv 抓了 3.14.5）；加 `.python-version`，Week 11 部署前确认与 Railway/Fly 运行环境对齐
- [ ] **真实 token 端到端验证延后**：Clerk dev 无前端时拿不到 session JWT（Account Portal 未激活、Dashboard 不导出 token）。Week 2+ 接 React 用 `getToken()` 时验「真 JWT→验签→JIT 写库」，确认返回 200 且 body 含 email（claim 透传）
- [ ] **CLERK_ISSUER 取值待真 token 核对**：现填 `https://literate-koala-34.clerk.accounts.dev`（Frontend API/issuer）；但 Account Portal 域名是 `literate-koala-34.accounts.dev`（无 `.clerk`，不同域）。首次真 token 若 401，先查 token 的 `iss` claim 是否与 CLERK_ISSUER 一致
- [ ] **CLERK_AUTHORIZED_PARTIES_RAW 现为空**（跳过 azp 校验）；接前端后填前端 origin（如 http://localhost:5173）启用
- [ ] networkless 验签延迟数据点未测（简历素材，真 token 时记缓存命中 vs 打 API 对比）
- [x] grams_per_unit 存储位置开放项闭合：D4 已定单列 NUMERIC 存于 Ingredient 表（非 ingredient_units 关系表），seed 已按此落地；D7 换算 = 查 ingredient.grams_per_unit 单次乘法
- [ ] docs/ERD.md 的 recipe_ingredients 节按 D5=B 更新：原稿只写 quantity_grams（方案 A），需补 input_amount + input_unit 两列，并改顶部"换算存入 quantity_grams"那行说明为"换算存 quantity_grams + 保留 input_amount/input_unit"

---

## 💡 简历素材池

> 开发过程中持续积累的数字、案例，最后写简历用。

### 性能数据

- API P99 响应时间：[待测]
- 数据库查询优化：[优化前 → 优化后]
- 缓存命中率：[待测]

### AI 相关数据

- 单次菜谱生成 token 成本：[待测]
- AI 缓存优化前后成本对比：[待测]（预期 ~60%）
- Prompt 迭代次数与质量提升：[待测]
- AI 调用失败率：[待测]

### 工程质量

- 测试覆盖率：[待测]
- CI/CD 流水线时间：[待测]

### 用户数据

- 注册用户数：0
- 周活跃用户数：0
- 用户反馈关键案例：[待收集]

### 架构设计素材（Week 1 ERD 产出）

- **15 张表的规范化 schema 设计**，含 7 个 trade-off 决策的完整文档（`docs/ERD.md` Design Decisions 节）
- **Event-sourced inventory with snapshot reconciliation**：双写架构 + 时间点回放 + shortage tracking 优雅降级
- **Two-level Recipe abstraction with hybrid tagging**：Recipe → Variant 两层 + 固定 purpose_tag 枚举 + 自由 recipe_variant_tags
- **AI observability layer**：独立 ai_generation_logs 表，prompt_input_hash 作缓存键，支撑限流 / A/B / 成本看板
- **Denormalized nutrition aggregates**：营养缓存 + 同步/异步混合 invalidation，21 餐周聚合性能优化

### 架构设计素材（Week 1 认证产出）

- **Hosted auth (Clerk) over self-rolled JWT**：安全/聚焦取舍，不重造 auth 轮子
- **Identity shadow pattern**：第三方身份与本地领域用户 bounded-context 解耦，业务 FK 指 internal UUID
- **JIT user provisioning (webhook deferred)**：首请求 upsert + IntegrityError 处理并发竞态；演进式设计
- **Networkless JWT verification with JWKS caching**：PyJWT 本地验 RS256/iss/azp/exp，run_in_threadpool 不堵事件循环（验签延迟数据点待补）
- **Deterministic constraint naming verified**：第一份 migration 实锤 `pk_users` / `uq_users_clerk_user_id`

### 架构设计素材（Week 1 骨架产出）

- **Async-first FastAPI skeleton**：domain-driven 结构 + async SQLAlchemy 2.0 + 单 asyncpg driver（含 Alembic async 迁移）+ liveness/readiness 健康检查分离
- **Deterministic constraint naming**：Base.metadata naming_convention，保证 Alembic autogenerate diff 干净可审查

### 可讲的故事

- [ ] 一个"性能优化"的故事（具体场景 + 数据）
- [ ] 一个"技术选型权衡"的故事
- [x] **一个"数据建模权衡"的故事**：Week 1 ERD 设计期间，针对食材单位（克归一化 vs 原始单位）、库存扣减（CRUD vs 事件流）、菜谱多版本（单层 vs Variant 两层）、标签系统（枚举 vs 自由）等关键问题做了 7 个决策的 trade-off 文档化，落地到 `docs/ERD.md` Design Decisions 节，每个决策都可单独讲 5 分钟
- [ ] 一个"用户反馈驱动迭代"的故事
- [ ] 一个"AI 工程化"的故事（成本控制、可靠性）
- [ ] 一个"线上 bug 排查"的故事
- [ ] 一个「第三方 auth 集成 + 安全设计」的故事（identity shadow + JIT 竞态处理 + networkless 验签）

### 架构设计素材（Week 2 食材层产出）

- **Version-pinned, reproducible USDA seed pipeline**：Foundation 2025-12 + SR Legacy 精选子集，CSV 快照而非实时 API，幂等 upsert（usda_fdc_id 作 key，ON CONFLICT DO UPDATE）；显式排除 Branded 避免搜索污染
- **Deterministic nutrient mapping across heterogeneous USDA sources**：处理 Foundation（Atwater 多 energy 行）vs SR Legacy（单一 1008）的 energy 歧义，定义 1008→2048→2047 优先级；四宏量 nullable 区分 unknown 与 measured-zero；numeric 避免周聚合浮点漂移
- **Forward-compatible schema**：高频可计算营养素走一等列（未来糖/钠 ADD COLUMN nullable）、长尾微量素预留 JSONB 路径，避免过早抽象——幂等 seed 让延迟加列零成本
- **Curated unit-to-gram mapping bridging USDA data gaps**：USDA per-100g 不含家庭计量，以 foodPortions 为机会性参考、人工裁决精选子集 grams_per_unit，落地克归一化（营养聚合 O(1)），绕开 UnitConversion 表的 N+1
- **Version-pinned, idempotent USDA seed pipeline (verified)**：Foundation 2026-04-30 + SR Legacy 精选 15 条子集，CSV 快照而非实时 API；committed manifest（人工裁决单位/选料）与 gitignored USDA 快照（营养）双 SoT 解耦；ON CONFLICT DO UPDATE 幂等 upsert，实测跑两次 row count 稳定不增重；显式排除 Branded + 按 data_type 过滤掉 market_acquisition/sample 等中间数据
- **Deterministic nutrient mapping across heterogeneous USDA sources**：实测同一生鸡胸 Foundation 用 Atwater 2048（112.2 kcal）无 1008、SR 用 1008（119 kcal），定义 1008→2048→2047 优先级消解 energy 歧义；四宏量 nullable 区分 unknown 与 measured-zero（实测肉类 carb=0 是真·0）；numeric 避免周聚合浮点漂移；规避新发布条目"有名无实"（2026-04-30 白面包营养全 NULL，回退 2019 版）

### 架构设计素材（Week 2 Recipe 层产出）

- **Dual-representation recipe quantities**：RecipeIngredient 同存归一化克数（O(1) 营养聚合）与用户原始输入（友好显示），少量冗余列规避运行时单位换算 N+1；写时换算一次、读时零换算
- **Intentional FK delete semantics**：recipe→variant→ingredient 三级，variant 依附 recipe 走 CASCADE、配料引用的 ingredient 走 RESTRICT（保护共享参考数据不被误删），同一张表两种 ondelete 体现关系语义
- **NULL-propagating nutrition aggregation (planned)**：聚合层延续 D2 的 0≠unknown，含 unknown 营养的配料使整道菜该营养标记为不完整而非静默归零；缓存到 Variant + 同步重算 + Phase 2 异步批量 invalidation 路径
- **Transactional recipe creation with inline conversion + aggregation**：单事务内建 Recipe+Variant+配料，逐条 D5 单位换算（克归一化）+ D6 营养聚合回写缓存列，全成功或全回滚；食材批量预查避免循环内 N+1；读取用 selectinload 三级预加载（variants→ingredients→ingredient）同样规避 N+1
- **Input validation at unit boundary**：配料单位限 default_unit/克（D5a），非法单位返回 422 带友好提示，把 D4 的"单非克单位+克兜底"约束落到写入校验

### 架构设计素材（Week 3 营养目标产出）

- **TDEE computation as pure, testable service**：Mifflin-St Jeor BMR → 活动系数 → 目标热量（可覆盖增减）→ 宏量分配（蛋白按体重/脂肪按热量百分比/碳水填余），纯函数零 IO、全 Decimal 避免浮点漂移、边界处理（other 性别取均值常数、碳水夹 0）
- **Computed-then-stored nutrition goals with override semantics**：算一次存库 + is_custom 标记区分系统建议 vs 用户手动覆盖，upsert on unique user_id 保证一人一条；身体数据（users 表）与目标（独立表）分离，目标可扩历史
- **First real cross-table FK on UUID identity**：user_nutrition_goals.user_id UUID FK→users，identity shadow 用户表首次被业务表引用，对齐真实 UUID 主键（区别于 recipes 因 UUID/BIGINT 不匹配留空的 FK）

### 架构设计素材（Week 4 餐食规划产出）

- **Two-tier meal planning with invisible default container**：显式 MealPlan（规划型用户，多计划/模板/重叠）+ default plan（记录型用户 quick-log 无感，get-or-create + 日期范围动态撑大）；同一结构服务两种用户心智，MealPlan 灵活日期范围无需改 schema
- **Authorization with existence-hiding**：资源归属校验（plan.user_id == current_user），非本人返回 404 而非 403，防止通过 id 枚举探测他人资源存在性
- **Cross-plan daily nutrition aggregation vs goals**：按 user+date join 跨所有 plan 汇总 entry（variant 缓存营养 × servings），对照 user_nutrition_goals 算宏量达标率；NULL 从食材层一路传播到达标率，未知营养不伪装成 0
- **Intentional FK semantics (3rd application)**：meal_plan_entries 的 plan_id CASCADE（餐次依附计划）vs recipe_variant_id RESTRICT（排入计划的菜谱受保护），依附/引用二分原则第三次落地

---

## 📝 每个 Chat 的总结存档

> 每次 chat 结束让 Claude 生成总结，粘贴到这里。
> 完整历史见 docs/CHANGELOG.md,此处仅保留最近 2-3 个 chat。

### [Chat 模板]

**日期**：YYYY-MM-DD  
**任务**：[简短描述]  
**完成**：

- ...

**决策**：

- ...

**下一步**：

- ...

**遗留问题**：

- ...

### Chat 11 — Week 3：TDEE 计算 + 营养目标

**日期**：2026-06-18
**任务**：定 N1–N4 决策，实现 TDEE 计算 service + 营养目标 CRUD

**完成**：

- N1–N4 全部锁定（见决策表）
- users 表加 5 身体字段（height_cm/weight_kg/age/biological_sex/activity_level，全 nullable）
- 新建 app/nutrition/ 域：UserNutritionGoal 模型（user_id UUID FK→users，CASCADE+unique）
- migration 842633d6643a：users 加列 + 建 user_nutrition_goals（FK 类型 UUID 实锤、CASCADE、unique 校验）
- services.py：compute_bmr（Mifflin-St Jeor）+ compute_nutrition_goal（BMR→TDEE→目标热量→宏量），全 Decimal，临时脚本验证 5 用例（含自定义 delta、other 性别边界）通过
- router.py：4 端点（PUT body-metrics 部分更新 / POST compute 算并存 / PUT override 手动覆盖 / GET 读），upsert on user_id，is_custom 区分系统算 vs 手动改
- 营养目标存库逻辑用临时脚本验证（compute 存 2094→override 改 1800→psql 直连确认库内 1800/is_custom=true）

**关键学习**：

- session 身份映射 + expire_on_commit=False：单 session 内 commit 后对象可能 stale（脚本读到旧值假象），生产每请求独立 session 天然规避；测试脚本需 db.expire_all()/refresh 强制刷新
- Mifflin-St Jeor 不需体脂率，平衡精度与填写门槛；蛋白按体重定是健身场景标准
- 强制关键字参数（def f(\*, ...)）防多参数按位置传错

**下一步**：Week 4 餐食规划 → 补每日营养汇总 → 简化版前端里程碑

**遗留问题**：

- nutrition 4 端点的真 token 端到端测试 defer 到前端（同 /users/me）；逻辑已用绕认证脚本验证
- 每日营养汇总挪 Week 4（依赖 meal_plan_entries）
- ERD 待校准：users.clerk_user_id（非 auth_provider_id）、user_nutrition_goals.user_id 改 UUID、recipe_ingredients 补 input_amount/input_unit（D5=B）

### Chat 12 — Week 4：餐食规划（Phase 1 收官）

**日期**：2026-06-19
**任务**：定 P1–P4 决策，实现 MealPlan/Entry 建模 + 计划 CRUD + quick-log + 每日营养汇总

**完成**：

- P1–P4 + 选2 全部锁定（见决策表）
- app/meal_plans/ 域：MealPlan（UUID FK→users、CHECK 日期、partial index 模板）+ MealPlanEntry（两 FK：plan CASCADE / variant RESTRICT）
- migration a9f5136bc290：两表落库，CHECK 约束 + partial index + 三 FK ondelete 全 review 通过
- schemas：计划/entry 的 Create/Read + quick-log + daily-summary（MacroSummary 三元组）
- services：meal_type_sort_key（防 dinner 字母序）+ get_or_create_default_plan + expand_plan_range
- router 9 端点：计划 CRUD（含归属校验 \_get_owned_plan，非本人 404）+ entry 加/删/complete（PATCH）+ quick-log（default plan 无感）+ daily-summary（跨 plan join + NULL 传播 vs 目标）
- ERD 校准：meal_plans.user_id UUID、recipe_ingredients 补 input_amount/input_unit、顶部加 user_id BIGINT→UUID 草图欠债备注

**关键学习**：

- 认证 vs 授权：get_current_user 是认证（你是谁），\_get_owned_plan 是授权（你能不能碰这资源）；非本人返 404 而非 403 防资源存在性泄漏
- 固定路径（/quick-log /daily-summary）需排在动态路径 /{plan_id} 前，避免被误当 plan_id
- HTTP 方法语义：PATCH 局部改（标记完成只翻 is_completed）vs PUT 整体替换
- MealPlan 是 entry 的必需容器非可选功能；default plan 让容器对记录型用户隐形

**下一步**：Clerk 前端骨架里程碑（真 token 验证积压认证端点）→ Week 5 库存

**遗留问题**：

- 全部认证端点（/users/me + 营养目标 + 计划全家桶）真 token 端到端测试集中到前端骨架里程碑
- default plan 的 quick-log 逻辑（get-or-create + 撑大）未真测，随前端骨架验证
- 每日营养汇总已补（Week 3 挪来的债还清）
- ERD 其余表 user_id 草图仍 BIGINT（inventory/shopping/notes/meal_logs），做到那周再校准

## Chat 13 — Clerk 前端骨架里程碑（完成）

**目标**：搭最小 React 前端，打通 Clerk 登录 → 拿真 JWT → 砸后端认证端点，
一次性真测积压的所有认证接口（此前只有 mock/curl 验证）。

**做了什么**
- 前端脚手架：Vite + React（纯 JS，非 TS——一次性骨架，正式前端 Week 10 再上分层 + TS）。
- 接 Clerk React SDK v5：`<ClerkProvider>` 包根、`.env.local` 存 publishable key
  （`VITE_` 前缀经 `import.meta.env` 注入）、`<SignedIn>/<SignedOut>/<SignInButton>/<UserButton>`。
- 后端 CORS：新增 `cors_allowed_origins_raw`（逗号分隔 property，复用 azp 同款模式），
  允许 `http://127.0.0.1:5173` + `http://localhost:5173` 双 origin。
- 启用 azp：`.env` 填 `CLERK_AUTHORIZED_PARTIES_RAW`（双 origin），否定测试确认能拦（错误 azp → 401）。

**端到端验证（全绿）**
- `GET /users/me` → 200，JIT 首次建 identity-shadow 行（sub→UUID，email claim 透传落库），
  二次调用 count 仍为 1（幂等确认）。
- 营养目标全链路：`PUT body-metrics`(200) → `POST compute`(200, TDEE≈2594 kcal maintenance)
  → `GET`(200 读回一致) → `PUT override`(200, upsert 覆盖为 2200, is_custom)。
- 真 token 解码核对：`iss=https://literate-koala-34.clerk.accounts.dev`（对上后端），
  `email` claim 存在（透传闭环），`exp-iat=60s`（轮换）。

**踩过的坑（简历素材）**
- `localhost` ≠ `127.0.0.1`：origin 层面不同，同时咬 CORS 允许列表和 Clerk azp——两处须与浏览器地址栏一致。统一改用 `localhost`。
- "假 CORS"：后端 500（DB 未起，asyncpg ConnectionRefused）时无法附加 CORS
---

## 📚 相关文档索引

> 项目过程中产出的设计文档、技术文档，方便后续 chat 快速定位。

- [x] `docs/ERD.md` — 数据库设计（ingredients 节已按 Week 2 D1–D4 修订）
- [ ] `docs/API_SPEC.md` — API 接口规范
- [ ] `docs/AI_PROMPTS.md` — AI prompt 设计与版本
- [ ] `docs/DEPLOYMENT.md` — 部署文档
- [ ] `README.md` — 项目主页（待补 v1 内容）
- [x] `docs/CHANGELOG.md` — 各 chat 详细总结归档
- [x] `docs/FRONTEND_MILESTONE.md` — Clerk 前端骨架里程碑任务书
- [x] `docs/MealForge_Project_Brief.md` — 项目总纲

---

_维护说明：每完成一个 chat 任务，更新"当前状态"、勾选"已完成"、追加"决策记录"和"chat 总结"。重新上传到 Project Knowledge 覆盖旧版本。_
