from django import template

register = template.Library()


@register.filter(name='ljust')
def ljust(value, length):
    return str(value).ljust(length)


@register.filter(name='sum_values')
def sum_values(queryset, field_name):
    return sum(getattr(item, field_name) for item in queryset)


@register.filter
def currency_mzn(value):
    try:
        value = float(value)
        return f"{value:,.2f} MZN".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "0,00 MZN"



register = template.Library()

@register.filter
def wrap_chars(value, n=10):
    """
    Quebra o texto em linhas de n caracteres.
    Retorna uma lista de linhas.
    """
    value = str(value)
    return [value[i:i+n] for i in range(0, len(value), n)]
