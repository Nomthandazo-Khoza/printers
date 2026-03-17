"""
Authentication blueprint: unified login, customer registration, logout.
All users (staff and customers) sign in at one login page; redirect by role after success.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user
from app import db
from app.models.user import User
from app.models.customer import Customer
from app.forms.auth_forms import LoginForm, CustomerRegistrationForm

auth_bp = Blueprint('auth', __name__)


def get_dashboard_url_for_user():
    """
    Return the dashboard URL for the currently logged-in user (staff or customer).
    Staff (admin or cashier): admin.dashboard. Customer: customer_portal.dashboard.
    """
    if current_user.is_authenticated:
        if current_user.is_admin or current_user.is_cashier:
            return url_for('admin.dashboard')
    if session.get('customer_id'):
        return url_for('customer_portal.dashboard')
    return None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Unified login for all users (staff and customers).
    Authenticate by email + password; try User (staff) first, then Customer.
    Redirect to the correct dashboard based on role.
    """
    if current_user.is_authenticated:
        return redirect(get_dashboard_url_for_user())
    if session.get('customer_id'):
        next_url = request.args.get('next') or url_for('customer_portal.dashboard')
        return redirect(next_url)

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data
        next_page = request.args.get('next')

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=form.remember_me.data)
            if next_page:
                return redirect(next_page)
            return redirect(get_dashboard_url_for_user())

        customer = Customer.query.filter_by(email=email).first()
        if customer and customer.check_password(password):
            session['customer_id'] = customer.id
            session['customer_portal'] = True
            if next_page:
                return redirect(next_page)
            return redirect(url_for('customer_portal.dashboard'))

        flash('Invalid email or password.', 'danger')
        return render_template('auth/login.html', form=form)

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Log out staff user (Flask-Login)."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/customer/register', methods=['GET', 'POST'])
def customer_register():
    """Customer registration for portal access."""
    form = CustomerRegistrationForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if Customer.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            form.password.data = request.form.get('password') or ''
            form.password_confirm.data = request.form.get('password_confirm') or ''
            return render_template('auth/customer_register.html', form=form)

        customer = Customer(
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            email=email,
            phone_number=form.phone_number.data.strip() or None,
            address=form.address.data.strip() or None,
        )
        customer.set_password(form.password.data)
        db.session.add(customer)
        db.session.commit()
        flash('Registration successful. You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        form.password.data = request.form.get('password') or ''
        form.password_confirm.data = request.form.get('password_confirm') or ''
    return render_template('auth/customer_register.html', form=form)


@auth_bp.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    """Redirect to unified login (keeps old links and bookmarks working)."""
    return redirect(url_for('auth.login'))


@auth_bp.route('/customer/logout', methods=['GET', 'POST'])
def customer_logout():
    """Log out customer from portal."""
    session.pop('customer_id', None)
    session.pop('customer_portal', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
