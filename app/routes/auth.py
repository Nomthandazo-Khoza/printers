"""
Authentication blueprint: staff login, customer login, customer registration.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app import db
from app.models.user import User
from app.models.customer import Customer
from app.forms.auth_forms import StaffLoginForm, CustomerLoginForm, CustomerRegistrationForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Staff login page. Admin and Cashier log in here.
    Redirects to appropriate dashboard after login.
    """
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('cashier.dashboard'))

    form = StaffLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html', form=form)

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('cashier.dashboard'))

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Log out current staff user."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


# --- Customer portal auth (separate from staff) ---

@auth_bp.route('/customer/register', methods=['GET', 'POST'])
def customer_register():
    """Customer registration for portal access."""
    form = CustomerRegistrationForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if Customer.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
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
        return redirect(url_for('auth.customer_login'))

    return render_template('auth/customer_register.html', form=form)


@auth_bp.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    """
    Customer portal login. Uses session to track customer (not Flask-Login User).
    For Phase 1 we use a simple approach; can be extended with a custom login manager.
    """
    form = CustomerLoginForm()
    if form.validate_on_submit():
        customer = Customer.query.filter_by(email=form.email.data.strip().lower()).first()
        if customer is None or not customer.check_password(form.password.data):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/customer_login.html', form=form)

        # Store customer id in session for customer portal (separate from staff login)
        from flask import session
        session['customer_id'] = customer.id
        session['customer_portal'] = True
        next_page = request.args.get('next') or url_for('customer_portal.dashboard')
        return redirect(next_page)

    return render_template('auth/customer_login.html', form=form)


@auth_bp.route('/customer/logout', methods=['GET', 'POST'])
def customer_logout():
    """Log out customer from portal."""
    from flask import session
    session.pop('customer_id', None)
    session.pop('customer_portal', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.customer_login'))
