from __future__ import annotations

from datetime import datetime

MODEL_CATALOG = {
    "2024": {
        "303": [
            {"code": "07", "label": "Base imponible 21%", "kind": "money"},
            {"code": "09", "label": "Cuota devengada", "kind": "money"},
            {"code": "28", "label": "Base deducible", "kind": "money"},
            {"code": "29", "label": "Cuota IVA deducible", "kind": "money"},
            {"code": "71", "label": "Resultado IVA", "kind": "money"},
        ],
        "130": [
            {"code": "01", "label": "Ingresos acumulados", "kind": "money"},
            {"code": "02", "label": "Gastos acumulados", "kind": "money"},
            {"code": "03", "label": "Rendimiento neto", "kind": "money"},
            {"code": "04", "label": "20% del rendimiento", "kind": "money"},
            {"code": "05", "label": "Pagos previos / a restar", "kind": "money"},
            {"code": "A ingresar", "label": "Total a ingresar", "kind": "money"},
        ],
        "100": [
            {"code": "0435", "label": "Base imponible general", "kind": "money"},
            {"code": "0460", "label": "Base imponible del ahorro", "kind": "money"},
            {"code": "0500", "label": "Base liquidable general", "kind": "money"},
            {"code": "0510", "label": "Base liquidable del ahorro", "kind": "money"},
            {"code": "0545", "label": "Cuota íntegra estatal", "kind": "money"},
            {"code": "0546", "label": "Cuota íntegra autonómica", "kind": "money"},
            {"code": "0609", "label": "Retenciones y pagos a cuenta", "kind": "money"},
            {"code": "0610", "label": "Resultado de la declaración", "kind": "money"},
            {"code": "0700", "label": "Declaración a devolver / a ingresar", "kind": "money"},
        ],
    },
    "2025": {
        "303": [
            {"code": "07", "label": "Base imponible 21%", "kind": "money"},
            {"code": "09", "label": "Cuota devengada", "kind": "money"},
            {"code": "28", "label": "Base deducible", "kind": "money"},
            {"code": "29", "label": "Cuota IVA deducible", "kind": "money"},
            {"code": "71", "label": "Resultado IVA", "kind": "money"},
        ],
        "130": [
            {"code": "01", "label": "Ingresos acumulados", "kind": "money"},
            {"code": "02", "label": "Gastos acumulados", "kind": "money"},
            {"code": "03", "label": "Rendimiento neto", "kind": "money"},
            {"code": "04", "label": "20% del rendimiento", "kind": "money"},
            {"code": "05", "label": "Pagos previos / a restar", "kind": "money"},
            {"code": "A ingresar", "label": "Total a ingresar", "kind": "money"},
        ],
        "100": [
            {"code": "0435", "label": "Base imponible general", "kind": "money"},
            {"code": "0460", "label": "Base imponible del ahorro", "kind": "money"},
            {"code": "0500", "label": "Base liquidable general", "kind": "money"},
            {"code": "0510", "label": "Base liquidable del ahorro", "kind": "money"},
            {"code": "0545", "label": "Cuota íntegra estatal", "kind": "money"},
            {"code": "0546", "label": "Cuota íntegra autonómica", "kind": "money"},
            {"code": "0609", "label": "Retenciones y pagos a cuenta", "kind": "money"},
            {"code": "0610", "label": "Resultado de la declaración", "kind": "money"},
            {"code": "0700", "label": "Declaración a devolver / a ingresar", "kind": "money"},
        ],
    },
    "2026": {
        "303": [
            {"code": "07", "label": "Base imponible 21%", "kind": "money"},
            {"code": "09", "label": "Cuota devengada", "kind": "money"},
            {"code": "28", "label": "Base deducible", "kind": "money"},
            {"code": "29", "label": "Cuota IVA deducible", "kind": "money"},
            {"code": "71", "label": "Resultado IVA", "kind": "money"},
        ],
        "130": [
            {"code": "01", "label": "Ingresos acumulados", "kind": "money"},
            {"code": "02", "label": "Gastos acumulados", "kind": "money"},
            {"code": "03", "label": "Rendimiento neto", "kind": "money"},
            {"code": "04", "label": "20% del rendimiento", "kind": "money"},
            {"code": "05", "label": "Pagos previos / a restar", "kind": "money"},
            {"code": "A ingresar", "label": "Total a ingresar", "kind": "money"},
        ],
        "100": [
            {"code": "0435", "label": "Base imponible general", "kind": "money"},
            {"code": "0460", "label": "Base imponible del ahorro", "kind": "money"},
            {"code": "0500", "label": "Base liquidable general", "kind": "money"},
            {"code": "0510", "label": "Base liquidable del ahorro", "kind": "money"},
            {"code": "0545", "label": "Cuota íntegra estatal", "kind": "money"},
            {"code": "0546", "label": "Cuota íntegra autonómica", "kind": "money"},
            {"code": "0609", "label": "Retenciones y pagos a cuenta", "kind": "money"},
            {"code": "0610", "label": "Resultado de la declaración", "kind": "money"},
            {"code": "0700", "label": "Declaración a devolver / a ingresar", "kind": "money"},
        ],
    },
}

SUPPORTED_YEARS = sorted(MODEL_CATALOG.keys(), key=lambda value: int(value))


def get_current_year() -> str:
    return str(datetime.now().year)


def get_model_config(year: int | str | None = None, model: str | None = None):
    selected_year = str(year or get_current_year())
    if selected_year not in MODEL_CATALOG:
        selected_year = SUPPORTED_YEARS[-1]

    if model is None:
        return MODEL_CATALOG[selected_year]

    normalized_model = str(model).upper().strip()
    model_cfg = MODEL_CATALOG[selected_year].get(normalized_model)
    if model_cfg is None:
        raise KeyError(f"Modelo {normalized_model} no disponible para el ejercicio {selected_year}")

    return model_cfg


def get_valid_codes(year: int | str | None = None, model: str | None = None):
    config = get_model_config(year=year, model=model)
    return [entry["code"] for entry in config]


def is_valid_model_code(year: int | str | None = None, model: str | None = None, code: str | int | None = None):
    if code is None:
        return False
    return str(code) in {str(item) for item in get_valid_codes(year=year, model=model)}
