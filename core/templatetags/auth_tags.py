# core/templatetags/auth_tags.py
from django import template

register = template.Library()

@register.filter
def is_admin(user):
    return user.groups.filter(name='Admin').exists()

@register.filter
def is_gerente(user):
    return user.groups.filter(name='Gerente').exists()

@register.filter
def is_vendedor(user):
    return user.groups.filter(name='Vendedor').exists()

@register.filter
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()

@register.simple_tag
def user_level(user):
    """Retorna o nível do usuário"""
    if user.is_superuser:
        return 'admin'
    elif user.groups.filter(name='Admin').exists():
        return 'admin'
    elif user.groups.filter(name='Gerente').exists():
        return 'gerente'
    elif user.groups.filter(name='Vendedor').exists():
        return 'vendedor'
    return 'sem-nivel'

@register.simple_tag
def can_access(user, *groups):
    """Verifica se usuário tem acesso a algum dos grupos"""
    return user.groups.filter(name__in=groups).exists() or user.is_superuser