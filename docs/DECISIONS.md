════════ Week 5 库存管理 · 决策记录 (I1–I10) ════════

I1  inventory_items 批次模型
    · 一食材多行（批次），非唯一
    · 扣减 FEFO：expires_at ASC NULLS LAST, purchased_at ASC
    · 库存不下穿负数；短缺另记，不写回库存
    · user_id UUID（清 Chat12 BIGINT 债）；expires_at/purchased_at 可空
    · 索引 (user_id, ingredient_id, expires_at)

I2  扣减机制：A′ 状态表 + append-only 流水
    · inventory_items = 当前真相源
    · inventory_transactions 流水（delta/reason/source_entry_id/时间）
    · 保留 90 天（可配），到期清理不影响当前库存
    · 撤销完成餐次 = 追加反向流水 + 回补库存

I3  单位：克本位地基（Week5）→ 换算率/自定义单位（Week6+）
    · 内部一律存基准单位(g/ml)；换算隔离在 I/O 边界
    · 终态：多单位+可改换算率+用户自定义单位（记录，暂不实现）

I4  临期提醒
    · 单级黄色：expires_at 在未来 N 天(默认3,可配)
    · 查询时算不落库；expires_at IS NULL 不提醒

I6  库存预扣视图（实现 Week6）
    · 实际库存(存储,非负) + 预计剩余(实时算,可负)
    · 预测视界默认7天可配/可全量

I7  缺口统一计算（实现 Week6）
    · compute_shortfall(user,start,end)：Σ未完成entry需求 − 库存SUM
    · 一函数多呈现（库存负数/采购待购），范围参数各自可传

I8  采购双来源（Week6）
    · auto(缺口生成,重算) / manual(手动,保留不覆盖) 隔离

I9  采购回流库存（Week6）
    · 填实际购买量 → 新增批次 + purchase 流水；expires_at 默认NULL可补
    · 购买单位↔库存单位 依赖 I3

I10 采购项属性（Week6）
    · add_to_inventory 开关（厨房纸=false）; 与 source 正交
    · 添加物品选择界面：选已有食材 / 创建新食材(填营养) / 创建非食材(纯文本)
════════════════════════════════════════════════