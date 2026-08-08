# MealForge 开发进度

> 这个文件追踪项目实际开发进度。每完成一个 chat 任务后更新。
> Claude 在新 chat 开始时应先读这个文件，了解当前状态。

---

## 🎯 当前状态

### Week 5 — 库存管理 ✅ 完成
- 批次模型 + FEFO 扣减 + 临期提醒 + 完整 CRUD，全部真 token 端到端验证
- 修复 Week 4 路由顺序 bug（daily-summary 被遮蔽）

### Week 6 — 智能采购 ✅ 完成
已完成：
- ShoppingList / ShoppingListItem 两表 + migration（部分唯一索引 `WHERE is_purchased=FALSE`、两个 CHECK、SET NULL/CASCADE 分工）
- **I7** `compute_shortfall`：未完成餐需求 − 库存；3 条 query 无 N+1；只算未完成餐（防双重计数）；过期餐排除（D2）
- **I8** 生成/重算：`generate_shopping_list` 物化 auto 快照；`regenerate_auto_items` 删未购 auto、保留已购 + manual
- **I9** `mark_item_purchased`：打勾购买 → 复用 `create_inventory_item` 原子回流
- **I10** 采购项属性：add_to_inventory / item_name / source / category_override
- **I6** `compute_preview` 库存预扣视图：实际 / 需求 / 预计剩余（可负 = 会缺）；抽 `_demand_and_stock` 与 compute_shortfall 共用；`GET /shopping-lists/preview`
- **I11** 用户自建内容（MVP）：ingredient + recipe 加 `visibility`（private/global）+ `created_by_user_id` 改 UUID+FK（清债 #5）；查询过滤"global 或自己建的"；创建端点固定 private/归属；决策 A 收敛 recipes.is_public → visibility
- `line_demand` helper（I13 单一真相源）
- REST 端点：采购清单 CRUD + regenerate + 加项 + 打勾购买 + preview；ingredient/recipe 创建 + 可见性列表
- **41 个测试**（缺口 9 / 生成 5 / 回流 5 / HTTP 6 / preview 5 / ingredient 可见性 6 / recipe 可见性 5）
- **CI/CD**（GitHub Actions：postgres service + ruff + pytest）+ README 徽章
- 修遗留 bug：`meal_plans/router` 未 import `MacroSummary`（CI lint F821 抓出）

### Week 7 — AI 菜谱生成 ✅ 完成（真实端到端跑通）
- `ai_generation_logs` 表 + `AiGenerationLog` 模型（成功/失败都记, kind 预留 meal_plan）
- **grounding**：库存食材清单喂进 prompt, AI 只能用清单内 ingredient_id；代码 `_validate` 硬校验兜底防幻觉
- **结构化输出**：`save_recipe` tool（function calling）强制结构化
- `app/ai/`：client(供应商 adapter) / prompts(纯函数) / recipe_tool(中立 schema) / services(核心) / schemas
- `POST /recipes/generate`：空库存 400 / AI 失败 502；落库 source=ai_generated + private + 归属 + 营养聚合
- **供应商 Anthropic → Gemini**：只改 client.py + 配置, 49 测试零改动（adapter 层实证）
- **49 个测试**（+AI 5 service + 3 endpoint）, 全 mock 不真调 API
- **真实验证**：Gemini 免费层生成「洋葱滑蛋炒鸡胸西兰花」, grounding 全部用库存食材 id, 营养自动算, $0

### Week 8 — AI 周计划 + 反向推荐 ✅ 完成（🏆 核心闭环里程碑达成）
- **功能 B 反向推荐**（纯查询, 不用 AI）：库存能做哪些已有菜谱做法; variant 级; 宽松匹配（缺 ≤2 列出缺啥）; 按缺料数排序; 无 N+1; `GET /recipes/recommendations`
- **功能 A AI 周计划**：AI 从已有可见菜谱挑 variant 排布 N 天（默认 7 天午晚）; grounding + 三重校验（variant_id/day_offset/meal_type）; 落 meal_plans/entries, plan_type=ai_generated; 日志 kind=meal_plan（Week7 预留用上）; `POST /meal-plans/generate`
- **client 泛化**：抽通用 `_call_tool`, recipe+plan 共用调用核（开闭原则）
- meal_plans.ai_generation_log_id 补 FK（迁移 d5a8c3f10e29）
- **62 个测试**（+反向推荐 5 +周计划 service 5 +周计划端点 3）
- CI lint 加 app/meal_plans
- 菜谱同名策略定案：允许同名(A) + 引导用 variant(D, 愿景)；清理 Week2 遗留重复数据

**🏆 核心闭环成立**：库存 → AI周计划 → 排餐 → 完成扣库存 → 采购缺口 → 清单 → 买 → 回流；反向推荐"库存能做啥"闭合入口。一个完整、能用的 AI 驱动膳食管理产品。

### 下一步 — Week 9：测试与性能优化
- 提升测试覆盖率（接 pytest-cov + 覆盖率徽章）
- 性能：AI 调用 P99、DB 查询优化、缓存（Redis 已规划）
- 全仓 lint 欠账清理 → CI 扩到 ruff check .
- AI 生成整周计划
- 反向推荐（库存 → 能做什么）
- CI lint 已含 app/ai；config 默认模型已改 gemini-3.1-flash-lite

### 项目基础信息

- **GitHub Repo**: https://github.com/junhao-logan/mealforge
- **本地路径**: `/home/junhao_logan/projects/mealforge/`
- **本次新增**: app/shopping/{models,schemas,services,router,__init__}.py、alembic/versions/1338b40ff5cc_add_shopping_tables.py、tests/{conftest,factories}.py、tests/shopping/{test_compute_shortfall,test_shopping_generation,test_purchase_reflow,test_shopping_api}.py、.github/workflows/ci.yml
- **本次改动**: app/main.py（注册 shopping router）、app/meal_plans/services.py（+line_demand）、app/inventory/services.py（deduct 调 line_demand）、app/meal_plans/router.py（修 MacroSummary import）、docs/ERD.md（shopping 表约束）、pyproject.toml（ruff 忽略 B008）、README.md（CI 徽章）
- **测试**: 25 个（真 Postgres，事务回滚隔离）；本地 `uv run pytest tests/ -v`

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
- [x] **Week 5**: 库存管理（批次 + FEFO 扣减 + 临期提醒 + CRUD，真 token 验证 ✅）
- [x] **Week 6**: 智能采购清单（I6–I11 全部完成 ✅：缺口/生成重算/回流/属性/预扣视图/用户自建内容 + REST 端点 + 41 测试 + CI）
- [x] **Week 7**: AI 菜谱生成（grounding + 结构化输出 + 供应商可切换 + 真实跑通 ✅）
- [x] **Week 8**: AI 周计划 + 反向推荐（🏆 核心闭环里程碑达成 ✅）
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

所有架构决策（含理由、备选方案、修订记录）集中在 [`docs/DECISIONS.md`](./DECISIONS.md)。
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
- [ ] **全仓 lint 欠账**（上 CI 时暴露）：`app/shopping`、`app/ingredients`、`app/recipes`、`tests` 已清并纳入 CI lint；其余模块（meal_plans / inventory / users / auth / nutrition 等）仍有 E501/I001 等风格问题待清。清完把 CI lint 扩到全仓（`ruff check .`）
- [ ] Week 6 输入即克简化：`purchased_grams = purchased_amount`（回流建批次沿用 Week 5 grams-only）；多单位换算（grams_per_unit）延后
- [ ] I11 愿景（依赖尚不存在的"公开菜谱"功能，见 DECISIONS）：①公开菜谱带出其引用的私有食材 ②私有→审核→公开状态机 ③公开时 AI/搜索去重
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

### 工程质量（Week 8 亮点）

- **adapter 泛化（开闭原则）**：Week 7 只有单菜谱生成, Week 8 抽出通用 `_call_tool`, 菜谱生成与周计划生成共用调用核; 加第三个 AI 功能只需新 tool schema + 瘦包装, 不改调用逻辑
- **三重防幻觉校验**：周计划里 AI 挑的每一餐, 校验 variant_id 在可见清单内 + day_offset 在范围内 + meal_type 合法; 任一不过判失败、记 kind=meal_plan 的 failed 日志、不写脏计划
- **推荐用集合运算避免 N+1**：反向推荐"库存能做啥"= 2 条固定查询（库存集合 + JOIN 拉全菜谱配料）+ 内存集合差集, 与菜谱数无关
- **一表多用的前瞻设计兑现**：Week 7 建日志表时预留 kind 字段, Week 8 周计划直接复用 kind='meal_plan', 无需新表
- **核心闭环打通**：AI 生成 → 排餐 → 扣库存 → 采购 → 回流 的完整数据流, 每一环都有测试守护

### 工程质量（Week 7 AI 亮点）

- **LLM 供应商可插拔（adapter 模式实证）**：AI 调用封装在 `app/ai/client.py` 一层；从 Anthropic 切到 Gemini **只改这一个文件 + 配置，49 个测试零改动全过**。业务逻辑不锁定单一厂商 —— 真换过、有证据
- **grounding 防 LLM 幻觉（双层）**：把真实库存食材清单喂进 prompt 约束 AI 只用清单内 id（软），代码再逐个校验 id 是否存在（硬）；即便 AI 幻觉出清单外食材也被拦截、判失败、绝不写脏数据
- **AI 调用审计/成本日志**：`ai_generation_logs` 记 prompt/response/token/status/error；成功失败都记。实战中一次 502（模型下线 404）被 error_message 精确定位 —— 失败留痕的价值当场兑现
- **配置化抗变更**：模型串号放 `.env`，`gemini-2.5-flash` 对新用户下线返 404 时，改一行配置换 `gemini-3.1-flash-lite` 即修复，不动代码
- **副作用隔离保可测**：调 API（有副作用/花钱）只在 client 一处，prompt 拼装/schema 是纯函数/纯数据；业务测试全程 mock，不依赖真 API

### 工程质量（Week 6 亮点）

- **行级可见性权限模型（I11）**：`visibility`(private/global) + `created_by_user_id` 两个正交维度，查询层一句 `WHERE visibility='global' OR created_by=me` 实现"看得见共享的 + 自己建的"；列表/详情/搜索全部受约束，别人私有内容按 id 直取也返 404（不泄漏存在性）
- **identity shadow 类型债清理**：`created_by_user_id` BigInteger→UUID+FK→users；手写迁移 + 数据回填（现有共享数据设 global，否则加字段后用户看不见）；downgrade 往返验证 + `alembic check` 漂移检测零差异
- **同一计算核两种视图（I6/I7）**：抽 `_demand_and_stock`，采购缺口（需求−库存，留正）与预扣视图（库存−需求，可负）共用；single source of computation
- **测试隔离用 per-test 事务回滚**：session 级建一次 schema（create_all），每个测试跑在事务里、结束回滚，测试间零残留。比每次 truncate/重建快，是生产级测试套件标准模式。HTTP 层测试用 `join_transaction_mode="create_savepoint"` 让端点内的 `commit()` 只提交 savepoint、外层仍整体回滚
- **测试断言的是设计决策而非 happy path**：25 个测试里，"不双重计数已完成餐""不算过期餐（D2）""用户隔离（JOIN 过滤）""重算保留已购/刷新未购""回流原子性" 等把正确性契约钉成可回归断言
- **引入 CI 静态检查即发现并修复一个未捕获的运行时 bug**：`meal_plans/router` 用了 `MacroSummary` 却未 import，daily-summary 端点会 `NameError` 崩溃；ruff F821 在首次 CI lint 时抓出
- **单一真相源隔离变化轴**：I13 需求公式（`quantity_grams × servings`）抽为 `line_demand`，库存扣减与采购缺口共用；Phase 3 batch-cooking 拆分"做/吃份数"时只改一处
- **探索性实时视图 vs 决策性物化快照**：同一 `compute_shortfall`，I6 做实时预扣视图（不落库）、I8 做采购快照（生成即物化），single source of computation 两种生命周期
- **派生数据物化的边界判断**：什么时候派生值该落库（有状态交互 + 稳定性需求，如采购清单），什么时候不该（纯探索视图）
- **约束名确定性**：SQLAlchemy `naming_convention` 让 Alembic autogenerate 产出可 review 的稳定 diff；实测验证 CHECK 名生成（避开 `ck_` 双前缀坑）
- **CI/CD**：GitHub Actions（postgres service 容器 + ruff + pytest），push/PR 自动跑，README 通过徽章


### AI 相关数据

- 单次菜谱生成 token 成本：[待测]
- AI 缓存优化前后成本对比：[待测]（预期 ~60%）
- Prompt 迭代次数与质量提升：[待测]
- AI 调用失败率：[待测]

### 工程质量

- 测试数：41（Week 6，真 Postgres + 事务回滚）；覆盖率：[待接 pytest-cov]
- CI/CD：GitHub Actions（postgres service + ruff + pytest），已上线

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