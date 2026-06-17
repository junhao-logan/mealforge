# app/ingredients/seed_ingredients.py
"""
独立幂等 USDA seed 脚本 (D3).
数据源: Foundation 2025-12 + SR Legacy 2018-04 CSV 快照 (D1), 版本钉死.
- 精选范围 + 人工单位字段: curated_ingredients.csv (committed)
- 营养 (per-100g): USDA food_nutrient.csv (gitignored 快照)
- upsert key: usda_fdc_id, ON CONFLICT DO UPDATE (幂等, 重跑安全)
运行: uv run python -m app.ingredients.seed_ingredients
"""
from __future__ import annotations

import asyncio
import csv
from decimal import Decimal
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from app.core.database import SessionLocal
from app.ingredients.models import Ingredient

# --- 路径 (S2: 下完 CSV 核对真实目录名) ---
SEED_DIR = Path(__file__).parent / "seed_data"
MANIFEST_PATH = SEED_DIR / "curated_ingredients.csv"
# fdc_id 全局唯一, 两份 food_nutrient.csv 都扫、用 manifest 集合过滤即可
USDA_FOOD_NUTRIENT_CSVS = [
    SEED_DIR / "usda" / "FoodData_Central_foundation_food_csv_2026-04-30" / "food_nutrient.csv",
    SEED_DIR / "usda" / "FoodData_Central_sr_legacy_food_csv_2018-04" / "food_nutrient.csv",
]

# --- USDA nutrient id 映射 (S3) ---
NUTRIENT_PROTEIN = 1003
NUTRIENT_FAT = 1004
NUTRIENT_CARB = 1005          # Carbohydrate, by difference
ENERGY_PRIORITY = (1008, 2048, 2047)  # D2; 三者皆 kcal, kJ 的(1062/268)天然排除
MACRO_IDS = {NUTRIENT_PROTEIN, NUTRIENT_FAT, NUTRIENT_CARB}
ENERGY_IDS = set(ENERGY_PRIORITY)


def normalize_name(name: str) -> str:
    return " ".join(name.lower().split())  # lower + strip + 折叠空格


def load_manifest() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with MANIFEST_PATH.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fdc_id = r["fdc_id"].strip()
            rows[fdc_id] = {  # dict 按 fdc_id 去重, 防 manifest 误写重复行
                "name": r["name"].strip(),
                "category": (r["category"] or "").strip() or None,
                "default_unit": r["default_unit"].strip(),
                "grams_per_unit": Decimal(r["grams_per_unit"]),
            }
    return rows


def extract_nutrients(target_ids: set[str]) -> dict[str, dict]:
    """stream food_nutrient.csv, 只留 target_ids, 提四宏量. S2 核对列名."""
    energy_cand: dict[str, dict[int, Decimal]] = {}
    macros: dict[str, dict[int, Decimal]] = {}

    for csv_path in USDA_FOOD_NUTRIENT_CSVS:
        if not csv_path.exists():
            raise FileNotFoundError(f"USDA 快照缺失: {csv_path}")
        with csv_path.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                fdc_id = r["fdc_id"].strip()        # TODO 核对列名
                if fdc_id not in target_ids:
                    continue
                nid = int(r["nutrient_id"])          # TODO 核对列名
                raw = r["amount"].strip()            # TODO 核对列名
                if not raw:
                    continue
                amount = Decimal(raw)                # str->Decimal 防浮点漂移
                if nid in MACRO_IDS:
                    macros.setdefault(fdc_id, {})[nid] = amount
                elif nid in ENERGY_IDS:
                    energy_cand.setdefault(fdc_id, {})[nid] = amount

    out: dict[str, dict] = {}
    for fdc_id in target_ids:
        m, e = macros.get(fdc_id, {}), energy_cand.get(fdc_id, {})
        # 注意: 用 `i in e` 判存在, 不判真假 —— 实测 0 kcal(如水)是 measured-zero, 保留为 0
        calories = next((e[i] for i in ENERGY_PRIORITY if i in e), None)
        out[fdc_id] = {
            "calories": calories,                    # None = unknown (D2)
            "protein": m.get(NUTRIENT_PROTEIN),
            "fat": m.get(NUTRIENT_FAT),
            "carbs": m.get(NUTRIENT_CARB),
        }
    return out


def build_rows(manifest: dict[str, dict], nutrients: dict[str, dict]) -> list[dict]:
    return [
        {
            "name": meta["name"],
            "name_normalized": normalize_name(meta["name"]),
            "category": meta["category"],
            "per_100g_calories": nutrients[fdc_id]["calories"],
            "per_100g_protein": nutrients[fdc_id]["protein"],
            "per_100g_carbs": nutrients[fdc_id]["carbs"],
            "per_100g_fat": nutrients[fdc_id]["fat"],
            "default_unit": meta["default_unit"],
            "grams_per_unit": meta["grams_per_unit"],
            "source": "usda",                        # S1 子决策: 硬编码
            "usda_fdc_id": fdc_id,
            # shelf_life_days: 留 null (S1 子决策, Week 5 backfill)
        }
        for fdc_id, meta in manifest.items()
    ]


async def upsert(rows: list[dict]) -> None:
    """
    幂等 upsert on usda_fdc_id.
    ⚠️ usda_fdc_id 是 *partial* unique index (WHERE usda_fdc_id IS NOT NULL),
       ON CONFLICT 必须带同样的 index_where, 否则 PG 匹配不到该 index.
    S4 未决: DO UPDATE 到底 SET 哪几列 —— 下面是占位(全列刷), 待 S4 定.
    """
    async with SessionLocal() as session:
        stmt = insert(Ingredient).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["usda_fdc_id"],
            index_where=Ingredient.usda_fdc_id.isnot(None),
            set_={  # TODO S4: 确认更新列集
                "per_100g_calories": stmt.excluded.per_100g_calories,
                "per_100g_protein": stmt.excluded.per_100g_protein,
                "per_100g_carbs": stmt.excluded.per_100g_carbs,
                "per_100g_fat": stmt.excluded.per_100g_fat,
                "name": stmt.excluded.name,
                "name_normalized": stmt.excluded.name_normalized,
                "category": stmt.excluded.category,
                "default_unit": stmt.excluded.default_unit,
                "grams_per_unit": stmt.excluded.grams_per_unit,
            },
        )
        await session.execute(stmt)
        await session.commit()


async def main() -> None:
    manifest = load_manifest()
    print(f"manifest: {len(manifest)} 条")
    nutrients = extract_nutrients(set(manifest.keys()))
    rows = build_rows(manifest, nutrients)
    no_energy = [r["usda_fdc_id"] for r in rows if r["per_100g_calories"] is None]
    if no_energy:
        print(f"⚠️  {len(no_energy)} 条无 energy: {no_energy[:10]}")
    await upsert(rows)
    print(f"✅ upsert {len(rows)} 条")


if __name__ == "__main__":
    asyncio.run(main())