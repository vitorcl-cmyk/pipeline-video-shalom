"""Helpers pequenos compartilhados entre schemas e routers."""
from datetime import date


def add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        # 29/02 em ano que o destino não é bissexto
        return d.replace(month=2, day=28, year=d.year + years)


def next_readjustment_date(data_inicio: date, data_ultimo_reajuste: date | None) -> date:
    base = data_ultimo_reajuste or data_inicio
    return add_years(base, 1)
