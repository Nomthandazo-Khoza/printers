"""
Role-based access decorators for City Printers CRM.
"""
from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def admin_required(f):
    """Restrict route to admin users only."""
    @wraps(f)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_view


def cashier_required(f):
    """Restrict route to cashier or admin (staff with operational access)."""
    @wraps(f)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not (current_user.is_admin or current_user.is_cashier):
            flash('Staff access required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_view


def staff_required(f):
    """Alias for cashier_required - any staff (admin or cashier)."""
    return cashier_required(f)
