# core/decorators.py
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from functools import wraps

# ========== DECORATORS POR GRUPO ==========

def admin_required(view_func):
    """Apenas Admin pode acessar"""
    def check_admin(user):
        return user.is_authenticated and (
            user.is_superuser or
            user.groups.filter(name='Admin').exists()
        )
    return user_passes_test(check_admin)(view_func)

def gerente_required(view_func):
    """Admin e Gerente podem acessar"""
    def check_gerente(user):
        return user.is_authenticated and (
            user.is_superuser or
            user.groups.filter(name__in=['Admin', 'Gerente']).exists()
        )
    return user_passes_test(check_gerente)(view_func)

def vendedor_required(view_func):
    """Todos os níveis podem acessar"""
    def check_vendedor(user):
        return user.is_authenticated and (
            user.is_superuser or
            user.groups.filter(name__in=['Admin', 'Gerente', 'Vendedor']).exists()
        )
    return user_passes_test(check_vendedor)(view_func)

# ========== DECORATORS POR PERMISSÃO ESPECÍFICA ==========

def permission_required(permission):
    """Decorator para permissão específica"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.has_perm(permission):
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return _wrapped_view
    return decorator

# ========== DECORATORS COM REDIRECT ==========

def grupo_required(*group_names, login_url=None, redirect_field_name=None):
    """Decorator para grupos específicos com redirect"""
    def in_groups(user):
        if user.is_authenticated:
            if user.is_superuser or user.groups.filter(name__in=group_names).exists():
                return True
        return False
    return user_passes_test(in_groups, login_url=login_url, redirect_field_name=redirect_field_name)