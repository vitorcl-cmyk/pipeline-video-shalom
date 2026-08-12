"""Helpers pequenos compartilhados entre schemas e routers."""
import calendar
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


def add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def next_caucao_correction_date(data_deposito: date, data_ultima_correcao: date | None) -> date:
    base = data_ultima_correcao or data_deposito
    return add_months(base, 1)


def next_due_date(dia_vencimento: int, today: date | None = None) -> date:
    """Próxima data em que o boleto do aluguel vence, a partir de hoje —
    usa o dia de vencimento do contrato (ex.: todo dia 5)."""
    today = today or date.today()
    dia = max(1, min(dia_vencimento or 1, 31))

    def _clamp(year: int, month: int) -> date:
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, min(dia, last_day))

    candidate = _clamp(today.year, today.month)
    if candidate < today:
        month = today.month + 1
        year = today.year
        if month > 12:
            month = 1
            year += 1
        candidate = _clamp(year, month)
    return candidate
