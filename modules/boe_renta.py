from __future__ import annotations

import json
import os
from typing import Dict, Iterable, List, Tuple


MODEL_CATALOG = {
    "2024": {
        "303": [
            {"code": "07", "label": "Base imponible 21%"},
            {"code": "09", "label": "Cuota devengada"},
            {"code": "28", "label": "Base deducible"},
            {"code": "29", "label": "Cuota IVA deducible"},
            {"code": "71", "label": "Resultado IVA"},
        ],
        "130": [
            {"code": "01", "label": "Ingresos acumulados"},
            {"code": "02", "label": "Gastos acumulados"},
            {"code": "03", "label": "Rendimiento neto"},
            {"code": "04", "label": "20% del rendimiento"},
            {"code": "05", "label": "Pagos previos / a restar"},
            {"code": "A ingresar", "label": "Total a ingresar"},
        ],
        "100": [
            {"code": "0435", "label": "Base imponible general"},
            {"code": "0460", "label": "Base imponible del ahorro"},
            {"code": "0500", "label": "Base liquidable general"},
            {"code": "0510", "label": "Base liquidable del ahorro"},
            {"code": "0545", "label": "Cuota íntegra estatal"},
            {"code": "0546", "label": "Cuota íntegra autonómica"},
            {"code": "0609", "label": "Retenciones y pagos a cuenta"},
            {"code": "0610", "label": "Resultado de la declaración"},
            {"code": "0700", "label": "Declaración a devolver / a ingresar"},
        ],
    },
    "2025": {
        "303": [
            {"code": "07", "label": "Base imponible 21%"},
            {"code": "09", "label": "Cuota devengada"},
            {"code": "28", "label": "Base deducible"},
            {"code": "29", "label": "Cuota IVA deducible"},
            {"code": "71", "label": "Resultado IVA"},
        ],
        "130": [
            {"code": "01", "label": "Ingresos acumulados"},
            {"code": "02", "label": "Gastos acumulados"},
            {"code": "03", "label": "Rendimiento neto"},
            {"code": "04", "label": "20% del rendimiento"},
            {"code": "05", "label": "Pagos previos / a restar"},
            {"code": "A ingresar", "label": "Total a ingresar"},
        ],
        "100": [
            {"code": "0435", "label": "Base imponible general"},
            {"code": "0460", "label": "Base imponible del ahorro"},
            {"code": "0500", "label": "Base liquidable general"},
            {"code": "0510", "label": "Base liquidable del ahorro"},
            {"code": "0545", "label": "Cuota íntegra estatal"},
            {"code": "0546", "label": "Cuota íntegra autonómica"},
            {"code": "0609", "label": "Retenciones y pagos a cuenta"},
            {"code": "0610", "label": "Resultado de la declaración"},
            {"code": "0700", "label": "Declaración a devolver / a ingresar"},
        ],
    },
}

BOE_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "boe_marcas.json")


def get_supported_years() -> List[str]:
    return sorted(MODEL_CATALOG.keys(), key=lambda year: int(year))


def get_model_codes(year: str, model_name: str) -> List[dict]:
    year_key = str(year)
    model_key = str(model_name).upper()
    if year_key not in MODEL_CATALOG:
        year_key = get_supported_years()[-1]
    if model_key not in MODEL_CATALOG[year_key]:
        raise KeyError(f"Modelo {model_name} no disponible para {year_key}")
    return MODEL_CATALOG[year_key][model_key]


def get_valid_codes(year: str, model_name: str) -> List[str]:
    return [entry["code"] for entry in get_model_codes(year, model_name)]


def _normalizar_code(value) -> str:
    return str(value).strip()


def validate_model_selection(year: str, model_name: str, codes: Iterable[str]) -> List[str]:
    valid = set(get_valid_codes(year, model_name))
    selected = [_normalizar_code(code) for code in codes]
    return [code for code in selected if code in valid]


def load_marks(path: str = BOE_DEFAULT_PATH) -> dict:
    try:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_marks(data: dict, path: str = BOE_DEFAULT_PATH) -> None:
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def auto_mark_model(year: str, model_name: str, calculated_values: dict) -> dict:
    valid_codes = get_valid_codes(year, model_name)
    result = {}
    for code in valid_codes:
        value = calculated_values.get(code, 0.0)
        result[code] = bool(float(value) > 0.0) if isinstance(value, (int, float)) else bool(value)
    return result


def get_model_summary_for_year(year: str, model_name: str, computed_values: dict) -> dict:
    valid = get_model_codes(year, model_name)
    summary = []
    for entry in valid:
        code = entry["code"]
        summary.append({
            "code": code,
            "label": entry["label"],
            "value": float(computed_values.get(code, 0.0) or 0.0),
        })
    return {"year": year, "model": model_name, "casillas": summary}


if __name__ == "__main__":
    print("Años soportados:", get_supported_years())
    print("303 2024:", get_valid_codes("2024", "303"))
    print("100 2025:", get_valid_codes("2025", "100"))
