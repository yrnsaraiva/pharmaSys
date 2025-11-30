# core/templatetags/date_filters.py
from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def add_days(date, days):
    """Adiciona dias a uma data"""
    try:
        days = int(days)
        return date + timedelta(days=days)
    except (ValueError, TypeError):
        return date

@register.filter
def days_until(date):
    """Calcula dias até uma data futura"""
    from django.utils import timezone
    if not date:
        return None
    today = timezone.now().date()
    if date < today:
        return 0
    return (date - today).days