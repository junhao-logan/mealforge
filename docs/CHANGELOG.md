# 开发历程存档
   > 各 chat 的详细总结,按时间正序。PROGRESS.md 只保留最近 2-3 个,
   > 其余归档于此,便于回溯但不占用工作台篇幅。
   
### Chat 1 — 开发环境搭建

**日期**：2026-05-13  
**任务**：Setup 阶段 Step 1-7（开发环境搭建）

**完成**：

- WSL2 + Ubuntu 22.04 LTS 安装并完成基础配置
- 系统更新 + 装齐 build-essential、curl、wget、git、unzip 等基础工具
- 配置 Git 全局身份（user.name / user.email / autocrlf=input）
- 通过 curl 安装 uv 0.11.14 到 ~/.local/bin/
- 通过 nvm 0.40.1 安装 Node 24.15.0 + npm 11.12.1
- 在 Docker Desktop 中开启 Ubuntu-22.04 WSL Integration
- 验证 docker run hello-world 成功
- 清理掉历史项目残留的 8GB Docker 镜像

**关键学习**：

- WSL2 是平台、Ubuntu 是发行版、Docker 容器是进程级隔离三者的区别
- 两个独立 PATH（Windows / WSL）+ appendWindowsPath 默认开启的特殊行为
- `which` / `dpkg -S` / `type -a` 等环境取证命令
- 镜像 vs 容器 vs Dockerfile 的关系
- 开发要在 Linux 原生文件系统里做，不能放 /mnt/c 或 /mnt/d

**遗留**：

- Windows 上 D:\nodeJs\ 还装着旧 Node，目前被 WSL 的 nvm 屏蔽，需要时再处理
- Step 8-10 待做：VS Code、GitHub SSH、项目骨架

**下一步**：
开新 chat 继续 Step 8：装 VS Code（Windows）+ Remote-WSL 扩展

### Chat 2 — Setup 收尾（Step 8-10）

**日期**：2026-05-13
**任务**：完成开发环境 Setup（Step 8-10）

**完成**：

- VS Code (Windows) + WSL 扩展配好，Remote-WSL 模式工作正常
- 在 `~/.ssh/` 生成 ed25519 SSH 密钥对
- 公钥添加到 GitHub Settings → SSH keys
- `ssh -T git@github.com` 验证通过，known_hosts 自动建立
- GitHub 网页建空仓库 https://github.com/junhao-logan/mealforge (Public, MIT, 无初始化文件)
- 本地建项目骨架：README.md + .gitignore + LICENSE
- `git init -b main` → `git add .` → `git commit` → `git remote add origin` → `git push -u origin main`
- 首个 commit hash: `3c828b7`，全程零密码（SSH 自动认证）

**关键学习**：

- VS Code 的 Remote-WSL 机制：Windows 装 VS Code 本体 + Server 自动装到 WSL；UI 在 Windows，所有操作在 Linux
- SSH key 的非对称加密原理：私钥本地永不外传，公钥到处贴；ed25519 算法是 2026 年默认推荐
- `ssh -T` 是"测试握手"不是"登录"，1 秒完事，无持久会话
- known_hosts 文件 = "信任过的服务器指纹列表"，防中间人攻击
- 三种 GitHub 认证方式互相独立：网页登录 / SSH key / Personal Access Token
- VS Code 在 SSH 流程里只是"显示窗口"，真正通信发生在 WSL 的 ssh 程序和 GitHub 服务器之间
- 排查 git 问题的标准动作：先 `pwd` + `ls -la` + `git status` + `git log --oneline`，再行动
- Claude Code 需要 CLI + Extension 两个组件配合，CLI 必须装在 WSL 里

**遗留**：

- Claude Code 待装（已加入清单）
- Windows 旧 Node 残留（已被 WSL nvm 屏蔽，暂不处理）

**下一步**：
开新 chat 进入 Week 1 主线 —— 设计 ER 图，搭建 FastAPI 项目骨架，配置 PostgreSQL + Redis Docker Compose

### Chat 3 — Week 1 数据库 ERD 设计

**日期**：2026-05-19
**任务**：设计 MealForge 数据库 schema，产出 `docs/ERD.md`

**完成**：

- 15 张表完整 schema（PostgreSQL 方言，含字段类型、约束、索引）
- 7 个核心设计决策的 trade-off 文档（每个都配了简历素材描述）
- Mermaid ER 图（GitHub 可直接渲染）
- 索引策略汇总表（含 partial index、复合索引、唯一约束的"服务于哪类查询"标注）
- MVP（15 张表立即建）与 Phase 2（`meal_logs` Week 5+ 加）的演进路径

**关键决策**（11 项，已全部进决策表）：

- 食材份量：改良方案 A——克数归一化 + Ingredient 表挂 unit 元数据（default_unit / grams_per_unit）
- 库存：快照（inventory_items）+ 事件流（inventory_transactions）双写
- 库存不足：不阻断，shortage_grams 记账 + CHECK quantity_grams ≥ 0
- MealPlan：任意起止日期 + 允许重叠 + plan_type 区分
- Recipe 两级抽象：Recipe（概念）→ Variant（具体做法），食材挂 Variant
- 标签系统：purpose_tag 固定 6 枚举 + recipe_variant_tags 自由标签双层混合
- 营养缓存：缓存到 RecipeVariant + 同步/异步混合 invalidation
- AI 调用日志独立成表（ai_generation_logs），prompt_input_hash 作缓存键
- inventory_transactions 区分 occurred_at vs created_at（支持补录）
- MVP 用 meal_plan_entries.is_completed 简化，Phase 2 演化出 meal_logs 表
- notes.rating 是 1-10 主观评分，语义由用户自定义

**关键学习**：

- 数据库设计的"产品决策权 vs 用户决策权"边界——核心分类系统属产品（固定枚举），个性化属用户（自由标签）
- Event sourcing 不是非黑即白——可以做成 snapshot + log 混合架构，读写两条路径分离
- 缓存字段的 invalidation 设计：同步 + 异步分级 + 时间戳兜底
- partial index 在业务驱动的查询场景下威力很大（`WHERE shortage_grams > 0`、`WHERE status = 'success'`）

**简历素材池新增**：

- "15-table normalized schema with documented trade-offs"
- "Event-sourced inventory with shortage tracking"
- "Two-level Recipe abstraction with hybrid tagging"
- "AI observability table powering rate limiting, A/B testing, and output caching"
- "Denormalized nutrition aggregates with hybrid invalidation"

**遗留问题**（Phase 2 或待用户反馈再决定）：

- 液体食材精度（油密度 ≠ 1）
- 食材别名 / 模糊搜索
- 多维度评分
- 多语言菜谱

**下一步**：

- 开新 chat，进入 Week 1 第二项主线：FastAPI 项目骨架 + Docker Compose（PostgreSQL + Redis）+ Alembic 初始化
- 新 chat 开始前需要先回答的 4 个架构决策：
  - Q-1：目录结构选 domain-driven（按领域）还是 layered（按层）
  - Q-2：SQLAlchemy 用 async（asyncpg）还是 sync（psycopg2）
  - Q-3：依赖管理用 pyproject.toml + uv 还是 requirements.txt
  - Q-4：本机 `docker --version` 和 `docker compose version` 跑一下确认环境

### Chat 4 — Week 1 FastAPI 骨架 + Docker Compose + Alembic

**日期**：2026-05-30
**任务**：搭 FastAPI 项目骨架，跑通 app→DB 链路

**完成**：

- domain-driven 骨架：app/core（config + database）+ app/health（liveness + readiness 双端点）
- async SQLAlchemy 2.0 引擎、AsyncSession 工厂、get_db 依赖、Base + naming_convention
- pydantic-settings 读 .env（DATABASE_URL / REDIS_URL / APP_ENV）
- Docker Compose：postgres:16-alpine + redis:7-alpine，各带 healthcheck
- Alembic async env.py（单 asyncpg driver，从 settings 注入 URL）
- uv sync 装 38 包 + 生成 uv.lock；app 以 editable 装入 venv
- 验证：/health → ok，/health/ready → database:ok（链路打通里程碑）
- Q-4 确认：Docker 28.5.1 / Compose v2.40.0（compose 文件不写 version 键正确）
- commit: `9e429d7`

**关键决策**（5 项，已进决策表）：

- domain-driven vs layered
- async vs sync ORM
- uv + pyproject vs requirements.txt
- Alembic async 单 driver vs 同步双 driver
- 约束 naming_convention

**关键学习**：

- WSL 原生文件系统 vs /mnt/d（项目必须在 ~/，挂载盘慢 10 倍；重启后容易迷失在 /mnt/d）
- liveness（不碰依赖）vs readiness（ping DB）健康检查的语义区别
- create_async_engine 在创建引擎时即 import asyncpg dialect（不是连接时才 import）

**遗留**：

- uv 默认抓了 Python 3.14.5，太新；建议加 .python-version 锁版本，Week 11 部署前确认 Railway/Fly 的 Python 版本对齐
- 认证方案未定（托管 Clerk/Supabase vs 自撸 JWT），决定 users 表 schema

**下一步**：

- 定认证方案 → 建 users 表 → 生成第一份 Alembic migration

### Chat 5 — Week 1 认证：Clerk + users 表 + auth 依赖

**日期**：2026-06-02
**任务**：定认证方案、建 users 表 + 第一份 migration、写 Clerk 验签依赖 + /users/me，收尾 Week 1

**完成**：

- 认证方案定为**托管 Clerk**（vs Supabase Auth vs 自撸 JWT）
- Clerk dev 实例：建 application、session token 加 email claim（`{{user.primary_email_address}}`）、Issuer = `https://literate-koala-34.clerk.accounts.dev`；建了测试用户 `001 test`（user_3EZN…RzQe）
- `app/users/models.py`：User 表（identity shadow），id 用 `gen_random_uuid()`（PG16 内置）
- 第一份 migration `911b07ee6f47_create_users_table.py`，已 `upgrade head`；`\d users` 结构 + 约束名（pk_users / uq_users_clerk_user_id）验证通过
- `app/core/config.py`：加 Clerk settings（clerk_issuer + clerk_authorized_parties_raw + 两个 property）
- `app/auth/dependencies.py`：networkless JWKS 验签 `get_current_user`（PyJWT + PyJWKClient + run_in_threadpool）+ JIT provisioning（IntegrityError 处理竞态）
- `app/users/schemas.py`（UserRead）+ `app/users/router.py`（/users/me）+ main.py 注册 router
- 装 `pyjwt[crypto]`；uvicorn 起服务，`/docs` 验证 /users/me 带锁、HTTPBearer 生效

**关键决策**（8 项，已进决策表）：托管 Clerk vs 自撸、Clerk vs Supabase、identity shadow、JIT（webhook 延后）、networkless JWKS、per-domain 增量 migration、clerk_user_id 仅 unique、dev azp 留空

**关键学习**：

- `uv run <cmd>` 跑 venv 内工具（alembic/uvicorn），免手动 activate
- Clerk dev 无前端时拿不到真 session JWT（Account Portal 需先登录激活、Dashboard 不导出 token）→ 真 token 验证天然属于前端阶段
- identity shadow / bounded context：auth provider 持有身份 source of truth，本地只存影子 + 业务关联

**遗留**：

- 真 token 端到端验证延后到前端（见技术债务）
- CLERK_ISSUER 取值、azp、验签延迟数据点待真 token 时核对/补
- README v1 未写（Week 1 唯一遗留）
- Python 版本未锁（uv 抓 3.14.5），Week 11 部署前对齐 Railway/Fly

**下一步**：

- （可选）补 README v1
- Week 2：USDA FoodData 导入 → Ingredient / Recipe / RecipeVariant / RecipeIngredient 模型 + migration → 菜谱 CRUD + 营养自动计算

### Chat 6 — Week 2 食材层：D1–D4 决策 + Ingredient 表

**日期**：2026-06-16
**任务**：锁定 Week 2 食材层设计决策（D1–D4），落地 Ingredient 模型 + 第二份 migration

**完成**：

- 落地顺序敲定：Ingredient 模型 → USDA seed → GET /ingredients → Recipe 三表 → 营养聚合 → Recipe CRUD
- D1–D4 全部锁定（见决策表）：USDA 子集/取法、四宏量 nullable + energy 优先级、独立幂等 seed、单 grams_per_unit
- docs/ERD.md ingredients 节按 D1–D4 修订
- app/ingredients/ 包 + Ingredient 模型（SQLAlchemy 2.0 Mapped/mapped_column 风格，对齐 users）
- alembic/env.py 补 \_ingredients_models import（防空 migration）
- migration 153bf345acc5：autogenerate → review（核对四宏量 nullable / partial unique index 的 WHERE / pk_ingredients 命名）→ upgrade，ingredients 表落库
- created_by_user_id 决定"留列不加 FK"：users.id 是 UUID 与 BIGINT 列类型不匹配，且 MVP 此列不写入，待"用户自定义食材"功能再连类型带 FK

**关键学习**：

- autogenerate 靠 Base.metadata 注册的表 diff，模型必须在 env.py 被 import（副作用 import + noqa）才看得见，否则生成空 migration
- autogenerate 必须人工 review：partial index 的 WHERE 子句、约束名、nullable 是高频出错点
- migration 是 schema 的"差异/版本历史"（类比 git commit），全局唯一一条链、与用户数据无关；seed 数据独立于 migration（D3）
- 0 ≠ unknown：营养数据用 NULL 表达未知，非 NULL 默认值会谎报数据

**下一步**：

- USDA seed 脚本（CSV 解析 + 1008→2048→2047 energy 取值 + 幂等 upsert + 人工/USDA 字段分离）
- 然后 GET /ingredients（分页 + name 过滤）

**遗留问题**：

- USDA CSV 已下载放置？（seed 前确认 Foundation 2025-12 + SR Legacy CSV 在项目 data 目录、已 gitignore）
- D5/D6/D7（Recipe 层）待食材跑通后定
- created_by_user_id 的 FK + BIGSERIAL/UUID 主键分叉，未来一并处理

### Chat 7 — Week 2 食材层：seed 脚本 S1–S3 + USDA 数据落地

**日期**：2026-06-16
**任务**：定 seed 实现层决策（S1–S4），下载/解压 USDA 数据，验证解析与 energy 取值

**完成**：

- S1 manifest 方案定稿：committed `curated_ingredients.csv`（fdc_id/name/category/default_unit/grams_per_unit）供人工字段，USDA 快照供营养，结构上分离（落实 D3）
- S1 子决策：shelf_life_days 留 null（Week 5 backfill）、source 脚本硬编码 'usda'
- 下载 Foundation 2026-04-30 + SR Legacy 2018-04 CSV，解压到 seed_data/usda/（已 gitignore）
- S2：food_nutrient.csv 列名两数据集一致（id/fdc_id/nutrient_id/amount/...），解析器无需改列名，路径填实
- S3：energy 取值规则实测通过（Foundation 2646170 落 2048=112.2；SR 171052 取 1008=119；kJ 1062 天然排除）
- 确认 SessionLocal 为 async_sessionmaker 工厂名（import 对齐）

**关键学习**：

- USDA food.csv 含大量中间过程数据（market_acquisition/sample_food），选料必须按 data_type 过滤只认成品
- 同一食材跨数据集 energy 用不同 nutrient_id（Foundation 2047/2048 vs SR 1008），D2 优先级规则的必要性被实测印证
- 0 ≠ unknown 在真数据上验证：carb=0 是 measured-zero（该存 0），整 nutrient 行缺失才是 NULL
- gitignored 快照下可复现性靠 fdc_id 稳定性兜底

**决策**：D1 版本号修正 2025-12→2026-04-30；新增「gitignored 快照 + fdc_id 兜底可复现」决策

**下一步**：grep 选料填 10–15 条 manifest → 跑真数据 extract_nutrients → 定 S4 → seed → GET /ingredients

**遗留问题**：

- SessionLocal 命名名实不符（async 工厂沿用 sync 老名），tech debt，将来重命名 AsyncSessionLocal
- S4（upsert 更新列集）待真数据后定
- D5/D6/D7（Recipe 层）食材跑通后定

### Chat 8 — Week 2 食材层：seed S4 + 真入库 + 幂等验证

**日期**：2026-06-16
**任务**：填 manifest（15 条精选）、dry-run 验数据、定 S4、真 seed 入库、验幂等

**完成**：

- manifest 填 15 条（蛋白/主食/蔬菜/乳制品，按选料铁律从真实 grep 结果裁决 fdc_id）
- dry-run（只读跑 extract_nutrients）肉眼验四宏量：西兰花 Foundation vs SR 数值一致、肉类 carb=0 正确存 0、白面包 2026-04-30 新条目营养全 NULL→回退 2019 版 325871
- S4 定方案 a（全刷）：manifest+USDA 唯一 SoT
- 真入库 15 条，营养收敛到 Numeric scale 位（112.20227→112.2、22.525→22.53）
- 幂等验证：跑两次 count 稳定 15，ON CONFLICT DO UPDATE 生效
- GET /ingredients 端点：schemas.py（IngredientRead，from_attributes，营养四列 Optional 透传 D2 语义，白名单不暴露 name_normalized/source/内部字段）+ router.py（APIRouter prefix=/ingredients；offset/limit 分页带 Query 范围校验；name 查询词同 normalize 后 LIKE 'xxx%' 走索引；order_by id 保证分页稳定）+ main.py include_router；/docs 测通三种（默认/翻页/name 过滤）

**关键学习**：

- Foundation 新发布日期条目可能"有名无实"（食材记录已建、营养未补），选料看 publication_date 新的要警惕全 NULL
- Numeric(precision, scale)：总位数/小数位，PG 入库自动四舍五入；用 Numeric 而非 Float 避免聚合浮点漂移
- .env 两个连接身份：DATABASE*URL（app via asyncpg）vs POSTGRES*\*（compose provision owner），psql 手连用后者；生产可拆 app/migration 角色
- D3 的"人工/营养分离"在 manifest 架构下已天然实现（物理双 SoT），不需 SQL 层再分离 → S4 可放心全刷
- FastAPI 声明式：函数签名 + Query/Depends 自动决定参数来源与校验；response_model 自动按 schema 过滤 ORM 对象字段；/docs（Swagger UI）由 OpenAPI 自动生成，非手写前端、是开发期接口试验台
- ORM 分层：model = 表定义 + 行载体（可读写库）；schema = API 出口形状（只读、白名单闸门）；db.execute 是 SQLAlchemy 提供、负责 stmt→SQL→asyncpg 发送→装成对象

**遗留问题**：

- 三文鱼/香蕉/橄榄油 grep 关键词需修正后补入 manifest
- GET /ingredients 三个小决策（分页风格/大小写 normalize/响应 schema）下段开头定
- D5/D6/D7（Recipe 层）待定
- 临时 dry-run 脚本已删，不入 commit

### Chat 9 — Week 2 Recipe 层：D5/D6/D7 + 三表建模

**日期**：2026-06-17
**任务**：定 Recipe 层三决策（D5/D6/D7），建 Recipe/RecipeVariant/RecipeIngredient 模型 + migration

**完成**：

- 食材层收尾确认：GET /ingredients 已跑通；grams_per_unit 单列开放项闭合（D4 已定）
- D5=B（克 + 原始输入双存）、D6（独立 service 同步聚合 + NULL 传播）、D7（读原始输入显示）锁定
- ERD review：原稿 recipe_ingredients 是方案 A（只存克），D5=B 需补两列 + 改 ERD（已记待办）；recipe_variants 的 total_grams/servings 支持 per-serving 营养，采纳
- app/recipes/{**init**,models}.py：三模型，SQLAlchemy 2.0 风格，含 relationship + back_populates + cascade
- 三个 FK 差异化：recipe_id/recipe_variant_id 走 CASCADE、ingredient_id 走 RESTRICT；created_by_user_id/ai_generation_log_id 留列不加 FK（UUID/BIGINT 不匹配 + ai_logs 表未建，同 ingredients）
- alembic/env.py 补 \_recipes_models import；migration 64c868f9d733 autogenerate → review（三表/FK 方向/ondelete/命名/nullable 四处核对）→ upgrade，三表落库验证（\dt 6 表、\d recipe_ingredients 两 FK 实锤 RESTRICT+CASCADE）

**关键学习**：

- relationship 是 ORM 对象导航（recipe.variants 免手写 JOIN），back_populates 双向绑定，cascade 在 ORM 层呼应 FK 的 CASCADE
- 同一表不同 FK 可用不同 ondelete 表达关系语义：依附关系 CASCADE、共享引用 RESTRICT
- autogenerate 日志只显示表/index，FK 和 ondelete 细节必须 cat 文件人工 review

**下一步**：Recipe CRUD（schemas → POST 创建含 D5 换算 → GET 读回）+ D6 聚合 service compute_variant_nutrition

**遗留问题**：

- docs/ERD.md recipe_ingredients 节待按 D5=B 更新
- created_by_user_id/ai_generation_log_id 的 FK 待 UUID/BIGINT 分叉 + ai_generation_logs 表建立后补
- recipe_variant_tags 表本期未建（自由标签，演进式延后）
---
### Chat 10 — Week 2 收尾：Recipe CRUD + 营养聚合（Week 2 完成）

**日期**：2026-06-17
**任务**：Recipe 层 schemas/services/router，POST 嵌套创建 + GET 读回，端到端测通

**完成**：

- 4 个 CRUD 形状决策：一次性嵌套创建 / service 校验单位 / 返回完整菜谱 / 列表+详情两 GET
- schemas.py：Create（入参，无 id/克/营养，Field 校验）vs Read（出参，含算好的值）两套；RecipeListItem 精简列表项
- services.py：resolve_grams（D5 换算，g×1 / default_unit×系数 / 其他 422）+ compute_variant_nutrition（D6 聚合，per_100g×克/100 累加，NULL 传播为不完整）
- router.py：POST 一个事务建 Recipe+Variant+配料（食材批量查避 N+1）→ D5 换算 → D6 聚合 → commit；GET 列表（精简）+ 详情（selectinload 预加载 variants→ingredients→ingredient 避 N+1）+ 404
- RecipeIngredient.ingredient relationship（纯 ORM 导航，无新列、无 migration）
- 测通：建菜（鸡胸 240g+米 185g+蛋 50g=475g，1024.5kcal）/ 非法单位 422 / 列表精简 / 详情嵌套 / 999→404

**关键学习**：

- back_populates 双向关系只设一端：variant.recipe=recipe 已自动加入 recipe.variants，再手动 append 会重复（踩坑，删掉手动 append 修复）
- 缓存列入库后按 Numeric scale 收敛（1024.540→1024.5），POST 返回是内存值、GET 读回是入库值
- --reload 服务独占终端前台，测试需开第二终端或用 /docs；一终端 Ctrl-C 会停服务（连接码 000）

**下一步**：Week 3 TDEE 计算 + 营养目标设置

**遗留问题**：

- docs/ERD.md recipe_ingredients 节待按 D5=B 补 input_amount/input_unit
- created_by_user_id/ai_generation_log_id FK 待补（UUID/BIGINT + ai_logs 表）
- recipe_variant_tags 表延后；Recipe 暂无 UPDATE/DELETE 端点（按需再加）
- 测试残留 id=1 重复菜谱（读取 bug 修复前建的，可 psql 清理）
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

## Chat 14 — Week 5 库存管理（完成）

**目标**：实现库存的批次模型、CRUD、FEFO 自动扣减、临期提醒；补齐相关技术债与文档。

**决策阶段**
- 开"设计决策会"，定 I1–I13（批次 FEFO / 状态表+流水 / 克本位 / 临期 / 预扣视图 /
  缺口统一 / 采购双来源 / 回流 / 采购项属性 / 自建内容 / entry.servings 语义）
- 新建 `docs/DECISIONS.md` 作为唯一决策记录处，D/N/P/I 系列全部集中

**实现（全部真 token 端到端验证）**
- 建表：`inventory_items`（批次，UUID user_id，D5=B 双表示，`location`）+
  `inventory_transactions`（append-only 审计），6 个 FK 的 ondelete 逐条 review（CASCADE/RESTRICT/SET NULL）
- CRUD：POST（入库+purchase流水，同事务）/ GET（FEFO序+临期状态，查询时算）/
  PATCH（盘点只改 quantity_grams，input_amount 快照不变）/ DELETE
- FEFO 扣减挂 `complete_entry`：跨批次 `min()` 逐批消耗、扣0不下穿、短缺分离返回、
  meal_consumption 流水带 source_entry_id、行锁防并发、幂等防重复扣、三表单事务
- 验证：单次完成跨 3 批次精确扣 240g；连跑两轮验 id tiebreaker + 零批次跳过 + 累积扣减

**修的 bug / 补的债**
- 🔴 路由顺序 bug（Week 4 埋）：`/daily-summary` 被 `/{plan_id}` 捕获→永远 422，
  静态路由移到动态前
- 排序非确定性：同过期日+purchased_at 均 NULL 时顺序随机 → 补 `id ASC` 全序兜底
- CHECK ≥ 0 约束（建表遗漏）→ 手写 migration 补（DB 层不变量兜底）
- `inventory_transactions.created_at`（建表遗漏）→ 补（支持事后补录时间回放）
- ERD 第 11/12 节约 10 处与实现不符 → 全节重写同步
- entry.servings 语义定案：= 配方倍数，扣减不除 variant.servings（对齐 Week4 营养聚合）

**踩坑固化（写进 DECISIONS 流程笔记）**
- Alembic 空 migration 静默"成功"三次 → checklist：apply 前 grep upgrade()、
  看 `Running upgrade` 那行、stamp 修指针
- 中文顿号混入代码 → SyntaxError

**收尾**：删前端脚手架、清测试数据、决策集中化、8 债清 4 defer 4

### Chat 14 — Week 6：智能采购清单（缺口 / 生成 / 回流 / CI）

**日期**：2026-07-28
**任务**：Week 6 智能采购 —— I7 缺口、I8 生成/重算、I9 回流、REST 端点、测试、CI

> 注：编号 14 为估计；Week 5 的 CHANGELOG 条目疑似未归档，待补。

**完成**：

- **ShoppingList / ShoppingListItem 两表 + migration**：部分唯一索引 `WHERE source='auto' AND is_purchased=FALSE`（重算幂等 + 保留已购）、两个 CHECK（forecast_range / has_identity）、SET NULL（溯源）与 CASCADE（依附）分工
- **I7 `compute_shortfall`**：未完成餐需求 − 库存，按食材聚合；3 条 query 无 N+1（JOIN 过滤用户 / IN 批量拉配料 / SUM 聚合库存）；只算未完成餐防双重计数；过期餐排除（D2）；量化到 0.01g 防微缺口
- **I8 生成/重算**：`generate_shopping_list` 物化缺口为 auto 快照；`regenerate_auto_items` 删未购 auto、保留已购 + manual
- **I9 `mark_item_purchased`**：打勾购买 → 复用 `create_inventory_item` 原子回流（建批次 + purchase 流水）；守卫：入库项必填购买量、拒重复购买
- **I10 采购项属性**：add_to_inventory / item_name / source / category_override
- **`line_demand` helper**：I13 公式抽为单一真相源，deduct 与 compute_shortfall 共用
- **REST 端点**：清单 CRUD + regenerate + 加项 + 打勾购买
- **测试基建 + 25 测试**：session 建 schema + 每测试事务回滚；HTTP 层 `join_transaction_mode='create_savepoint'` 回滚；`api_client` fixture 用 `dependency_overrides` 绕过 Clerk
- **CI/CD**：GitHub Actions（postgres service + ruff + pytest）+ README 徽章
- **修遗留 bug**：`meal_plans/router` 未 import `MacroSummary`（CI ruff F821 抓出，daily-summary 会 NameError）

**关键决策（本次敲定）**：

- 预测视界 `forecast_start/end` **落库**：重算沿用同一区间，清单语义边界稳定
- 同食材 auto + manual **允许两行**：partial unique 只管未购 auto，保留来源信息，展示层归组
- 重算**保留已购 auto**：已购是冻结的历史事实，未购才是活的预测（对齐 I6/I7 探索 vs 决策）
- auto 项**物化快照**而非读时计算：采购清单是决策性、要稳定可打勾，不同于 I6 探索性实时视图

**关键学习**：

- SQLAlchemy `naming_convention` 会给 CHECK 加 `ck_<表>_` 前缀，`name=` 只传语义后缀（否则双前缀）
- 部分唯一索引管辖范围要 = 重算变更范围（`is_purchased=FALSE`），否则保留已购时插新 auto 会撞唯一约束
- 上 CI 首次 lint 即暴露历史欠账（88 项）+ 一个真 bug；B008（FastAPI Depends 默认值）是公认误报，全局忽略

**遗留**：

- I6 库存预扣视图、I11 用户自建内容未做（Week 6 范围内）
- 全仓 lint 欠账 88 项待清（CI lint 暂限 `app/shopping tests`）
- Week 5 CHANGELOG 条目待补归档

**下一步**：
Week 6 收尾（I6 / I11 / lint 清理）或直接进 Week 7（AI 菜谱生成）；可选加覆盖率徽章

### Chat 15 — Week 6 收尾：预扣视图（I6）+ 用户自建内容（I11）

**日期**：2026-07-28
**任务**：Week 6 最后两块 —— I6 库存预扣视图、I11 用户自建内容（ingredient + recipe）

**完成**：

- **I6 库存预扣视图**：抽 `_demand_and_stock` 共享计算核；`compute_preview` 返回每食材 实际/需求/预计剩余（可负=会缺）；`GET /shopping-lists/preview`（注册在 `/{list_id}` 前避免路由遮蔽）；`compute_shortfall` 重构复用该核（25 旧测试守护，行为不变）
- **I11 用户自建内容（MVP，ingredient + recipe 两级）**：
  - `created_by_user_id`：BigInteger → UUID + FK→users（清类型债 #5），手写迁移 + `USING NULL::uuid`（全列 NULL 已验证）
  - 加 `visibility`(private/global)；数据回填现有共享数据为 global
  - 决策 A：`recipes.is_public` 收敛进 `visibility`，删 is_public
  - 查询过滤：`WHERE visibility='global' OR created_by=me`；创建端点固定 private/归属/source；别人私有按 id 直取返 404
  - ingredient/recipe 列表端点加认证（原先无 auth）
- 测试 25 → **41**（+I6 preview 5、+ingredient 可见性 6、+recipe 可见性 5）
- CI lint 范围扩到 `app/ingredients`、`app/recipes`；顺带修 `recipes/services.py` 历史 lint 欠账

**关键决策/学习**：

- **I11 范围重定**：用户提出"公开菜谱应带出其引用的私有食材（标注私人创建）"，推翻了纯内容级 `visibility='global'` 过滤 —— 该场景依赖尚不存在的"公开菜谱"功能。故 MVP 只做私有创建 + 过滤，把"带出私有食材 / 审核转公开 / AI 去重"三层写进 DECISIONS 愿景
- 决策 A：is_public 收敛进 visibility（单一概念）
- 迁移验证三板斧：完整链 upgrade + downgrade 往返 + `alembic check` 漂移检测
- 带索引的列改类型：PG 自动重建索引，alembic 无需显式处理（沙箱验证）

**遗留**：

- I11 愿景三层（依赖公开菜谱功能）
- 全仓 lint 欠账：已清 shopping/ingredients/recipes/tests，其余模块待清后扩 CI 到全仓

**下一步**：Week 7 AI 菜谱生成（项目核心亮点）

**Week 6 状态：I6–I11 全部完成，智能采购彻底收官 ✅**

### Chat 16 — Week 7：AI 菜谱生成（grounding + 结构化输出 + 供应商可切换，真实跑通）

**日期**：2026-08-07
**任务**：Week 7 AI 菜谱生成 —— 从库存生成、结构化输出、审计日志、供应商换 Gemini

**完成**：

- **基建**：`ai_generation_logs` 表 + 模型（成功/失败都记, token 输入输出分开, kind 预留 meal_plan）；
  `recipes.ai_generation_log_id` 补 FK（两表互相引用, 均可空）
- **`app/ai/` 新域**：client(供应商 adapter) / prompts(纯函数) / recipe_tool(中立 JSON schema) /
  services(核心) / schemas
- **grounding**：库存食材清单喂进 prompt, AI 只能用清单内 ingredient_id；`_validate` 硬校验兜底
- **结构化输出**：`save_recipe` function calling 强制结构化
- **service**：校验先于持久化（失败无需回滚, 只记 failed 日志）；成功菜谱+日志同事务两向链 +
  复用 compute_variant_nutrition
- **端点** `POST /recipes/generate`：空库存 400 / AI 失败 502
- **供应商 Anthropic → Gemini**：只改 client.py + config + 依赖, services/端点/49 测试零改动全过
- **49 测试**（+AI service 5 + endpoint 3, 全 mock）
- CI lint 加 app/ai；config 默认模型 → gemini-3.1-flash-lite

**关键决策/学习**：

- **输入方式重定**：不做多轮聊天（省 token）；用"结构化选项(免费)+一句自由文本(便宜)+单次生成"；
  食材清单限量
- **供应商可切换实证**：adapter 层让换 Gemini 只动一个文件, 业务零改 —— 面试硬素材
- **模型会下线**：`gemini-2.5-flash` 对新用户返 404, 改 `.env` 一行换 3.1-flash-lite 即修复 →
  串号必须配置化
- **失败留痕的价值**：真出 502 时 `ai_generation_logs.error_message` 精确记下 404 原因, 一眼定位
- **Gemini 免费层坑**：开 billing 即失去免费层；配额可能被砍；免费层数据用于训练

**真实验证（$0）**：Gemini 免费层生成「洋葱滑蛋炒鸡胸西兰花」, ingredients 全部是库存食材 id
(鸡胸1/西兰花10/洋葱12/鸡蛋6), 营养自动聚合(371 kcal / 56g 蛋白), source=ai_generated + private

**遗留**：

- `.python-version` 锁 3.14, 部署前降 3.12（google-genai 在 3.14 有 DeprecationWarning, 第三方库内部, 忽略）
- D-AI 愿景：生成来源演进（库存→全库→网络热门 + I11(c) 自动建食材）
- 全仓 lint 欠账：已清 shopping/ingredients/recipes/ai/tests, 其余待清

**下一步**：Week 8 — AI 周计划 + 反向推荐（里程碑：核心闭环完成）

**Week 7 状态：AI 菜谱生成真实端到端跑通 ✅**

### Chat 17 — Week 8：AI 周计划 + 反向推荐（🏆 核心闭环里程碑）

**日期**：2026-08-07
**任务**：Week 8 两个功能 —— 反向推荐(纯查询) + AI 周计划(排布已有菜谱)

**完成**：

- **功能 B 反向推荐**（纯查询, 不用 AI）：`recommend_recipes` —— 库存能做哪些已有可见菜谱做法;
  variant 级; 宽松匹配（缺 ≤max_missing 默认2, 列出缺啥）; 按缺料数升序; 无 N+1（库存集合 +
  JOIN 拉全 + 内存差集）; `GET /recipes/recommendations`; 真实验证通过
- **功能 A AI 周计划**：`generate_meal_plan` —— AI 从可见菜谱 variant 清单挑选, 排 N 天（默认7天午晚）;
  grounding + 三重校验（variant_id/day_offset/meal_type）; 落 meal_plans/entries, plan_type=ai_generated;
  日志 kind=meal_plan; `POST /meal-plans/generate`（空目录 400 / AI 失败 502）
- **client 泛化**：抽通用 `_call_tool`, recipe+plan 共用（开闭原则）
- meal_plans.ai_generation_log_id 补 FK（迁移 d5a8c3f10e29, 往返+漂移检测通过）
- **62 测试**（+5 推荐 +5 周计划 service +3 端点）; CI lint 加 app/meal_plans
- 菜谱同名策略 A+D 存档（D-R2）; 清 Week2 遗留重复 "Chicken rice bowl"

**关键决策/学习**：

- 反向推荐用纯查询而非 AI —— 与 Week7 "AI 从库存现编" 互补, 集合运算又快又准（D-R1）
- 两个同名菜谱是测试误建, 不是 bug —— 引出同名策略 A(允许)+D(引导用 variant)（D-R2）
- adapter 泛化: 加 AI 功能只写 schema+包装, 印证 Week7 封装的可扩展性
- 一表多用: Week7 预留的 kind 字段 Week8 直接复用, 不建新表
- conftest 漏 import app.ai.models 导致单独跑测试时 FK 找不到目标表 —— 补齐（models 必须 import 才被 create_all 收到）

**🏆 里程碑：核心闭环成立** —— 库存→AI周计划→排餐→扣库存→采购→回流, 反向推荐闭合入口。
完整、能用的 AI 驱动膳食管理产品。

**遗留**：

- 周计划第二版"不足时 AI 生成补齐"（D-AI4 愿景）
- 全仓 lint 欠账: 已清 shopping/ingredients/recipes/ai/meal_plans/tests, 其余待清
- `.python-version` 锁 3.14, 部署前降 3.12

**下一步**：Week 9 — 测试与性能优化

**Week 8 状态：核心闭环里程碑达成 ✅🏆**