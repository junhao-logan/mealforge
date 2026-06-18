# 简化版前端里程碑（Clerk 骨架）

> 目的：不是正式前端（正式 UI 在 Week 10）。这是一个**最小骨架**，
> 唯一任务是打通"Clerk 登录 → 拿真 session JWT → 调通带认证的后端端点"，
> 一次性清掉积压的"写了但没真测"的认证端点。

## 何时做

**Week 4 餐食规划完成后**插入（约 2–3 小时）。不早做（先把后端 CRUD 主线推完）、
不拖到 Week 10（认证端点会越积越多，集中验证风险大）。

## 背景：为什么需要

dev 阶段 Clerk 无前端时拿不到真 session JWT（Account Portal 未激活、
Dashboard 不导出 token），导致以下端点**代码写完但从未端到端验证**：

- `GET /users/me`（Week 1）
- `PUT /users/me/body-metrics`（Week 3）
- `POST /users/me/nutrition-goal/compute`（Week 3）
- `PUT /users/me/nutrition-goal`（Week 3）
- `GET /users/me/nutrition-goal`（Week 3）
- （Week 4 起会继续新增带认证端点）

## 范围（只做这些，不多做）

- 一个极简 React 页面（Vite + React，不上 shadcn/Tailwind 美化，那是 Week 10）
- 集成 Clerk React SDK：登录组件 + 登录后用 `getToken()` 拿 JWT
- 几个按钮，分别调上面列出的端点，把 token 放 `Authorization: Bearer` 头
- 页面上原样打印后端返回的 JSON（验证用，不做 UI）

## 这个里程碑要验证 / 解决的具体清单

- [ ] **真 JWT → 验签 → JIT 写库**：首次带真 token 调 `/users/me`，确认返回 200 且
      body 含 email（claim 透传），库里 users 表新增影子行
- [ ] **CLERK_ISSUER 核对**：现填 `https://literate-koala-34.clerk.accounts.dev`；
      若 401，查 token 的 `iss` claim 是否与此一致（Account Portal 域名是
      `literate-koala-34.accounts.dev` 无 `.clerk`，是不同域，需确认用哪个）
- [ ] **启用 azp 校验**：`CLERK_AUTHORIZED_PARTIES_RAW` 现为空（跳过 azp）；
      接前端后填前端 origin（如 `http://localhost:5173`）启用
- [ ] **networkless 验签延迟数据点**（简历素材）：记录 JWKS 缓存命中 vs 打 API 的延迟对比
- [ ] **营养目标全链路真测**：body-metrics → compute → override → get，走真 HTTP 确认
      （此前仅用绕认证脚本验证过存库逻辑）

## 完成标志

上述清单全部勾掉，且至少 5 个带认证端点在真 token 下返回预期结果。
完成后此里程碑结束，回到后端主线（Week 5 库存）。