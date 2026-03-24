"""
Main blueprint: index and role-based redirect.
"""
from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """
    Root URL. Redirect staff/customer sessions to dashboards; otherwise show public homepage.
    """
    if current_user.is_authenticated:
        if current_user.is_admin or current_user.is_cashier:
            return redirect(url_for('admin.dashboard'))
    # Check if customer is in session (portal)
    from flask import session
    if session.get('customer_id'):
        return redirect(url_for('customer_portal.dashboard'))
    return render_template('home.html')
