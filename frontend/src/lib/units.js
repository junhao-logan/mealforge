// src/lib/units.js
// 食物单位清单(A2 单位本位)。value = 存进后端 nutrition_basis_unit 的值; label = 显示。
import i18n from '@/i18n'

// 质量/容量: 克/毫升 用英文 value 'g'/'ml'(与食材库/USDA 一致, 后端据此识别可换算克);
// 其余为"单位本位"原子单位, value == label(中文), 后端视为该食材唯一单位、不换算克。
export const FOOD_UNITS = [
    { value: 'g', label: '克' },
    { value: 'ml', label: '毫升' },
    { value: '个', label: '个' },
    { value: '只', label: '只' },
    { value: '根', label: '根' },
    { value: '片', label: '片' },
    { value: '块', label: '块' },
    { value: '瓣', label: '瓣' },
    { value: '颗', label: '颗' },
    { value: '粒', label: '粒' },
    { value: '条', label: '条' },
    { value: '张', label: '张' },
    { value: '份', label: '份' },
    { value: '袋', label: '袋' },
    { value: '包', label: '包' },
    { value: '盒', label: '盒' },
    { value: '罐', label: '罐' },
    { value: '瓶', label: '瓶' },
    { value: '桶', label: '桶' },
    { value: '杯', label: '杯' },
    { value: '碗', label: '碗' },
    { value: '勺', label: '勺' },
    { value: '汤匙', label: '汤匙' },
    { value: '茶匙', label: '茶匙' },
    { value: '把', label: '把' },
    { value: '束', label: '束' },
    { value: '枝', label: '枝' },
    { value: '朵', label: '朵' },
    { value: '头', label: '头' },
    { value: '枚', label: '枚' },
    { value: '段', label: '段' },
    { value: '斤', label: '斤' },
    { value: '两', label: '两' },
    { value: '滴', label: '滴' },
    { value: '撮', label: '撮' },
]

// 已知单位 → 中文显示(含食材库英文单位)。未知回退原值。
const ZH_LABELS = {
    g: '克', ml: '毫升', kg: '千克', l: '升',
    piece: '个', cup: '杯', block: '块', slice: '片', clove: '瓣',
    tbsp: '汤匙', tsp: '茶匙',
}
for (const u of FOOD_UNITS) ZH_LABELS[u.value] = u.label

// 英文显示。value 不变(仍存中文进后端), 仅改显示。多个中文量词在英文里合并(个/只/颗/枚→piece)。
const EN_LABELS = {
    g: 'g', ml: 'ml', kg: 'kg', l: 'L',
    piece: 'piece', cup: 'cup', block: 'chunk', slice: 'slice', clove: 'clove',
    tbsp: 'tbsp', tsp: 'tsp',
    个: 'piece', 只: 'whole', 根: 'stick', 片: 'slice', 块: 'chunk', 瓣: 'clove',
    颗: 'piece', 粒: 'grain', 条: 'strip', 张: 'sheet', 份: 'portion', 袋: 'bag',
    包: 'pack', 盒: 'box', 罐: 'can', 瓶: 'bottle', 桶: 'tub', 杯: 'cup', 碗: 'bowl',
    勺: 'spoon', 汤匙: 'tbsp', 茶匙: 'tsp', 把: 'handful', 束: 'bunch', 枝: 'sprig',
    朵: 'floret', 头: 'head', 枚: 'piece', 段: 'segment', 斤: 'jin', 两: 'liang',
    滴: 'drop', 撮: 'pinch',
}

// 按当前界面语言返回单位显示名。传入 lng 可显式指定(如 'zh'/'en'), 缺省用 i18n 当前语言。
// 组件调用时因 useTranslation 会在切换语言时重渲染, 从而拿到新语言的 label。
export function unitLabel(u, lng) {
    const lang = lng || i18n.language || 'en'
    const isZh = lang.startsWith('zh')
    if (isZh) return ZH_LABELS[u] || u
    return EN_LABELS[u] || ZH_LABELS[u] || u
}

// 质量/容量单位默认按"每 100"填营养; 其余原子单位按"每 1"。
export function defaultBasisFor(unitValue) {
    return unitValue === 'g' || unitValue === 'ml' ? 100 : 1
}
