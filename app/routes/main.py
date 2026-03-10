"""
Main blueprint: index and role-based redirect.
"""
from flask import Blueprint, redirect, url_for
from flask_login import current_user

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """
    Root URL. Redirect to dashboard based on role, or to login.
    """
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        if current_user.is_cashier:
            return redirect(url_for('cashier.dashboard'))
    # Check if customer is in session (portal)
    from flask import session
    if session.get('customer_id'):
        return redirect(url_for('customer_portal.dashboard'))
    return redirect(url_for('auth.login'))
