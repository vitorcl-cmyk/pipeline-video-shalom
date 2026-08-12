"""Helpers pequenos compartilhados entre schemas e routers."""
import calendar
import re
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


def only_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def validar_cpf(cpf: str) -> bool:
    cpf = only_digits(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    def digito(cpf_parcial: str) -> int:
        soma = sum(int(d) * peso for d, peso in zip(cpf_parcial, range(len(cpf_parcial) + 1, 1, -1)))
        resto = (soma * 10) % 11
        return 0 if resto == 10 else resto

    d1 = digito(cpf[:9])
    d2 = digito(cpf[:9] + str(d1))
    return cpf[-2:] == f"{d1}{d2}"


def validar_cnpj(cnpj: str) -> bool:
    cnpj = only_digits(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    def digito(cnpj_parcial: str) -> int:
        pesos = (
            [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
            if len(cnpj_parcial) == 13
            else [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        )
        soma = sum(int(d) * p for d, p in zip(cnpj_parcial, pesos))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    d1 = digito(cnpj[:12])
    d2 = digito(cnpj[:12] + str(d1))
    return cnpj[-2:] == f"{d1}{d2}"


class DocumentoInvalido(Exception):
    pass


def identificar_documento(valor: str) -> tuple[str, str]:
    """Retorna ('cpf'|'cnpj', digitos_limpos) ou lança DocumentoInvalido."""
    digitos = only_digits(valor)
    if len(digitos) == 11:
        if not validar_cpf(digitos):
            raise DocumentoInvalido(f"CPF inválido: {valor}")
        return "cpf", digitos
    if len(digitos) == 14:
        if not validar_cnpj(digitos):
            raise DocumentoInvalido(f"CNPJ inválido: {valor}")
        return "cnpj", digitos
    raise DocumentoInvalido(
        f"Documento com {len(digitos)} dígitos não é CPF (11) nem CNPJ (14): {valor}"
    )


def formatar_cpf(cpf: str) -> str:
    cpf = only_digits(cpf)
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def formatar_cnpj(cnpj: str) -> str:
    cnpj = only_digits(cnpj)
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
