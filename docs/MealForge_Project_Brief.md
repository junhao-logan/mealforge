# MealForge — 项目知识库文档

> 这是一个个人全栈项目的完整规划文档。作为 Claude Project 的知识库，帮助 AI 助手理解项目背景、目标和当前进度，从而提供精准的协助。

---

## 一、项目背景与目标

### 1.1 个人背景

- **身份**：计算机专业应届生，还有约 6 个月毕业
- **目标岗位**：海外 Software Engineer（全栈 / 后端方向）
- **技术偏好**：主用 Python
- **技术基础**：前后端都有一些经验，能独立完成 CRUD 级别项目
- **可投入时间**：每周 10-20 小时

### 1.2 项目的战略目的

这个项目不是练手玩具，而是**简历核心项目**。需要同时满足：

1. **可讲故事**：来源于真实痛点，能在面试中讲出 ownership 叙事
2. **技术深度**：包含足够多的工程亮点，能撑住面试官深挖
3. **可上线、有用户**：海外面试官特别看重 end-to-end delivery
4. **AI 集成**：当下海外市场最吃香的方向，是简历加分关键
5. **GitHub 像产品**：README、commit、架构图、demo 都要专业

---

## 二、产品定位

### 2.1 项目名称

**MealForge**（暂定，可后续调整）

### 2.2 一句话定位

> 面向减脂 / 健身人群的 AI 驱动饮食规划平台，覆盖"营养目标 → 菜谱规划 → 库存管理 → 智能采购"完整闭环。

### 2.3 解决什么痛点

作者本人减脂健身过程中亲历的痛点：

- 每天吃什么、卡路里和宏量营养素如何匹配——**现有 App 只到这一层**
- 一周买什么菜、早中晚怎么搭配
- 菜谱怎么管理、什么时候做什么菜
- 冰箱里剩了什么、临期了什么、能做什么菜
- 整个流程没有一个 App 能一站式解决

### 2.4 市场差异化

| 现有方案 | 局限 |
|---|---|
| MyFitnessPal、薄荷健康 | 只解决"记录"，不规划 |
| 下厨房、Yummly | 有菜谱，但不结合营养目标和库存 |
| Mealime、Eat This Much | 有规划，但缺库存和反向推荐 |

**MealForge 的差异点**：营养目标 + 菜谱 + 库存 + 采购的**闭环** + **AI 增强**。

---

## 三、核心功能模块

### 3.1 模块清单

#### M1. 营养目标层
- 用户输入：身高、体重、年龄、性别、活动水平、减脂/增肌/维持目标
- 系统计算：TDEE、每日目标热量、宏量营养素分配（蛋白/碳水/脂肪）
- 用户可自定义覆盖系统计算结果

#### M2. 菜谱库
- 菜谱字段：名称、食材列表（含份量）、做法步骤、营养信息（自动计算）、标签、烹饪时间、难度、图片
- 标签体系：餐类型（早/午/晚/加餐）、风格（中/西/日）、特性（高蛋白/低碳/快手）
- 来源：用户自定义 + AI 生成 + 预置基础菜谱库

#### M3. 餐食规划器（核心）
- 周视图日历，每天三餐 + 可选加餐
- 拖拽 / 点选菜谱填充
- 实时显示每日营养是否达标
- 一键复制上周、模板保存

#### M4. 库存管理
- 食材增删改、数量、单位、保质期
- 做完一餐自动扣减库存
- 临期提醒（红/黄状态）
- 拍小票 / 外卖单识别入库（AI 增强）

#### M5. 智能采购清单
- 自动计算：本周菜单食材需求 - 现有库存 = 待购清单
- 按超市分区归类（蔬果区 / 肉蛋区 / 主食区 / 调味料）
- 导出 / 打印 / 分享

#### M6. 反向推荐（亮点）
- 输入：当前库存
- 输出：能做的菜谱列表，按"匹配度 + 营养契合度"排序
- 支持"我有 X、Y、Z，能做什么菜"自然语言查询

#### M7. 笔记与复盘
- 每餐 / 每日笔记：好吃程度、感受、调整建议
- 周复盘：营养达标率、最常做菜谱、采购成本

### 3.2 AI 增强功能（简历加分项）

| 功能 | 技术实现 |
|---|---|
| **AI 菜谱生成** | LLM + structured output（JSON schema），输入需求生成完整菜谱并存库 |
| **AI 周计划生成** | 给定营养目标 + 偏好 + 库存，LLM 生成一周菜单 |
| **图片识别食材** | 多模态 API（GPT-4 Vision / Claude），拍冰箱 → 识别 → 入库存 |
| **自然语言查询** | "这周蛋白质够吗"、"剩下的菠菜能做啥"，AI 直接答 |
| **小票解析** | 拍超市小票 → OCR + LLM 结构化 → 自动入库存 |

**MVP 阶段至少实现前两个**。

---

## 四、技术栈

### 4.1 选型与理由

```
后端:    FastAPI + SQLAlchemy 2.0 + Alembic
数据库:  PostgreSQL（主）+ Redis（缓存 + Celery broker）
AI:      Anthropic Claude API（主）+ OpenAI API（备选）
前端:    React + TypeScript + Tailwind CSS + shadcn/ui
状态管理: TanStack Query + Zustand
认证:    Clerk 或 Supabase Auth
异步任务: Celery
部署:    Railway / Fly.io
容器化:  Docker + Docker Compose
CI/CD:   GitHub Actions
监控:    Sentry（错误）+ Logfire / Posthog（产品分析）
测试:    pytest + pytest-asyncio + Playwright（E2E）
```

### 4.2 为什么这样选

- **FastAPI**：异步性能、类型友好、自动 OpenAPI 文档、海外流行度高
- **PostgreSQL**：海外主流，比 MySQL 更受欢迎，支持 JSONB 适合存灵活字段
- **shadcn/ui + Tailwind**：让 UI 看起来专业，避免"作业感"
- **Railway / Fly.io**：比 AWS 简单，免费额度够 demo，部署快
- **Claude API**：structured output 强、长 context、价格友好

---

## 五、技术亮点（面试谈资）

每一项都要在开发中**记录数据**，简历和面试都用得上。

| 技术点 | 体现方式 |
|---|---|
| **数据库设计** | 菜谱-食材多对多 + 份量、营养聚合计算、库存事务一致性 |
| **缓存策略** | Redis 缓存营养计算、热门菜谱、AI 生成结果 |
| **AI 集成工程化** | Structured output、prompt 版本管理、token 成本控制、失败重试 |
| **后台任务** | Celery 异步生成周计划、定时临期提醒、批量营养计算 |
| **API 设计** | RESTful、分页、过滤、错误处理、限流（slowapi） |
| **测试** | pytest 单元 + 集成测试，覆盖率 >80% |
| **性能优化** | N+1 查询识别与优化、批量计算、查询计划分析 |
| **可观测性** | 结构化日志、Sentry 错误监控、关键指标埋点 |
| **CI/CD** | GitHub Actions 自动测试 + 部署 |
| **真实部署** | HTTPS、自定义域名、健康检查、Docker 多阶段构建 |

---

## 六、数据模型概览

核心实体（详细 ER 图后续生成）：

- **User**: 基础信息、营养目标
- **Ingredient**: 食材库（名称、单位、每 100g 营养、分类、保质期天数）
- **Recipe**: 菜谱（基本信息 + 做法 + 标签）
- **RecipeIngredient**: 菜谱-食材关联表（含份量）
- **MealPlan**: 周计划
- **MealPlanEntry**: 每餐条目（日期 + 餐次 + 菜谱）
- **InventoryItem**: 用户库存条目（食材 + 数量 + 入库日期 + 过期日期）
- **ShoppingList**: 采购清单（按周生成）
- **Note**: 笔记（关联餐次或日期）
- **AIGenerationLog**: AI 生成日志（用于成本追踪和 prompt 优化）

---

## 七、12 周开发计划

每周投入 10-20 小时。**核心原则：永远先有能跑的版本，再迭代**。

### Phase 1: MVP 基础（Week 1-4）

**Week 1 — 设计与搭建**
- 需求细化、ER 图、API 设计文档
- FastAPI 项目骨架、PostgreSQL、Docker Compose
- 认证集成、用户注册登录
- 写 README v1

**Week 2 — 菜谱与食材**
- 食材库（导入 USDA FoodData Central 公开数据集）
- 菜谱 CRUD + 营养自动计算
- 前端：菜谱列表、详情、创建表单

**Week 3 — 营养目标**
- TDEE 计算器
- 用户营养目标设置 UI
- 每日营养汇总组件

**Week 4 — 餐食规划 v1**
- 周日历视图
- 选菜谱填充每餐
- 每日营养达标实时显示
- **里程碑：自己能用起来**

### Phase 2: 核心闭环（Week 5-8）

**Week 5 — 库存管理**
- 库存 CRUD
- 做完餐次自动扣减
- 临期提醒

**Week 6 — 智能采购清单**
- 菜单 - 库存 = 待购
- 按品类分组
- 导出功能

**Week 7 — AI 菜谱生成**
- Claude API 集成
- Structured output（JSON schema）
- Prompt 设计、错误处理、成本追踪

**Week 8 — AI 周计划 + 反向推荐**
- 一键生成一周菜单
- 反向推荐："我有什么能做什么"
- **里程碑：核心闭环完成**

### Phase 3: 打磨与上线（Week 9-12）

**Week 9 — 测试与性能**
- pytest 测试覆盖核心 API
- N+1 查询优化、加缓存
- **记录优化前后数据**（简历素材）

**Week 10 — 前端打磨**
- shadcn/ui 重做 UI
- 响应式、深色模式
- Loading / 错误 / 空状态

**Week 11 — 部署上线**
- 部署 Railway / Fly.io
- 自定义域名 + HTTPS
- Sentry 监控
- 写 3-5 篇技术博客

**Week 12 — 推广与迭代**
- 发 Reddit、小红书、Twitter
- 收集反馈、修 bug
- **目标：30-50 真实用户**
- 补 README"用户反馈"章节

---

## 八、简历呈现示例

完成后简历上的描述（参考模板，最终用真实数据替换）：

> **MealForge** — AI-powered meal planning platform | [github] [live demo]
> *Python, FastAPI, PostgreSQL, Redis, Celery, React, TypeScript, Claude API*
> 
> - Built end-to-end SaaS solving inventory-aware meal planning, acquired 50+ active users in first month with ~70% week-2 retention
> - Designed normalized PostgreSQL schema for recipes, ingredients, meal plans, and inventory; optimized N+1 queries reducing API latency from 2.1s to 280ms (87% improvement)
> - Integrated Claude API with structured outputs for AI recipe and weekly plan generation; implemented prompt versioning, retry logic, and Redis caching, reducing per-user LLM cost by 60%
> - Implemented async task queue (Celery + Redis) for weekly plan generation and shopping list compilation
> - Achieved 85% test coverage with pytest; deployed via Docker + GitHub Actions CI/CD to Fly.io with Sentry monitoring

---

## 九、协作约定（给 Claude 的工作指引）

> 这一节是给 Claude Project 中的 AI 助手看的，告诉它如何最好地协助开发。

### 9.1 工作风格偏好

- 用户是认真做项目的应届生，不是初学者，**不要过度解释基础概念**
- 但用户也不是资深工程师，遇到关键设计决策**讲清楚 trade-off**
- 用户目标是海外 SDE 面试，**所有建议都应该考虑"如何成为简历/面试素材"**

### 9.2 协作模式

- **优先讨论设计，再写代码**：遇到新功能先聊数据模型、API 设计、技术选型
- **代码要解释 why，不只是 how**：尤其是非显然的选择
- **主动提示"可记录的数据"**：每次优化都问"优化前后数据记下来了吗"
- **主动推动里程碑**：当前在第几周？该完成什么？落后了吗？

### 9.3 当前进度追踪

> 用户进入新 chat 后，请先询问当前处于哪一周、上次做到哪里。

- [ ] Week 1: 设计与搭建
- [ ] Week 2: 菜谱与食材
- [ ] Week 3: 营养目标
- [ ] Week 4: 餐食规划 v1
- [ ] Week 5: 库存管理
- [ ] Week 6: 智能采购清单
- [ ] Week 7: AI 菜谱生成
- [ ] Week 8: AI 周计划 + 反向推荐
- [ ] Week 9: 测试与性能
- [ ] Week 10: 前端打磨
- [ ] Week 11: 部署上线
- [ ] Week 12: 推广与迭代

### 9.4 简历素材积累清单

每个 Phase 结束时，提醒用户更新以下数据：

- API P99 / 平均响应时间（优化前/后）
- 数据库查询次数优化记录
- AI token 成本与优化数据
- 测试覆盖率
- 真实用户数与留存率
- 关键技术决策的复盘文档

---

## 十、风险与备选方案

### 10.1 时间风险

- 12 周计划是**理想节奏**，留有 1-2 周缓冲
- 如果进度落后，**优先砍 AI 高级功能**（图片识别、小票解析），保住核心闭环 + AI 菜谱生成

### 10.2 范围风险

- **绝对不做**的事：移动 App、社交功能、营养师付费咨询、第三方电商对接
- 范围一旦扩张，立刻砍回核心

### 10.3 技术风险

- AI 成本失控 → 加用户级限流、缓存生成结果
- 数据库性能问题 → 先解决再继续加功能，不要"债务"上线

---

## 附录 A：参考资源

- **营养数据**：USDA FoodData Central API（公开免费）
- **FastAPI 最佳实践**：https://github.com/zhanymkanov/fastapi-best-practices
- **System Design 参考书**：Alex Xu《System Design Interview》Vol 1 & 2
- **海外面试**：NeetCode 150、Pramp、interviewing.io

---

*文档版本 v1.0 — 项目启动文档，开发过程中持续迭代。*
