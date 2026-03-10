"""
Customer portal blueprint: dashboard, place request, my orders, receipts, profile.
"""
from flask import Blueprint, render_template, redirect, url_for, session
from app.models.customer import Customer
from app.models.order import Order
from app.models.receipt import Receipt

customer_bp = Blueprint('customer_portal', __name__)


def get_current_customer():
    """Return current customer from session or None."""
    cid = session.get('customer_id')
    if not cid:
        return None
    return Customer.query.get(cid)


def customer_login_required(f):
    """Require customer to be logged in to portal."""
    from functools import wraps
    @wraps(f)
    def decorated_view(*args, **kwargs):
        if not session.get('customer_id'):
            return redirect(url_for('auth.customer_login'))
        return f(*args, **kwargs)
    return decorated_view


@customer_bp.route('/')
@customer_bp.route('/dashboard')
@customer_login_required
def dashboard():
    """
    Customer portal dashboard: summary and recent orders for this customer.
    """
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.customer_login'))

    my_orders = Order.query.filter_by(customer_id=customer.id).order_by(
        Order.created_at.desc()
    ).limit(10).all()

    return render_template(
        'customer/dashboard.html',
        customer=customer,
        my_orders=my_orders,
    )


@customer_bp.route('/request')
@customer_login_required
def place_request():
    """Place a service request (info page until full flow is built)."""
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.customer_login'))
    return render_template('customer/place_request.html', customer=customer)


@customer_bp.route('/orders')
@customer_login_required
def my_orders():
    """List all orders for the logged-in customer."""
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.customer_login'))
    orders = Order.query.filter_by(customer_id=customer.id).order_by(
        Order.created_at.desc()
    ).all()
    return render_template('customer/my_orders.html', customer=customer, orders=orders)


@customer_bp.route('/orders/<int:order_id>')
@customer_login_required
def order_detail(order_id):
    """View one order (only if it belongs to this customer)."""
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.customer_login'))
    order = Order.query.filter_by(id=order_id, customer_id=customer.id).first_or_404()
    return render_template('customer/order_detail.html', customer=customer, order=order)


@customer_bp.route('/receipts')
@customer_login_required
def receipts():
    """List receipts for this customer's paid orders."""
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.customer_login'))
    # Receipts for orders belonging to this customer
    receipts_list = Receipt.query.join(Order).filter(
        Order.customer_id == customer.id
    ).order_by(Receipt.generated_date.desc()).all()
    return render_template('customer/receipts.html', customer=customer, receipts_list=receipts_list)


@customer_bp.route('/profile')
@customer_login_required
def profile():
    """View and manage profile (view for now)."""
    customer = get_current_customer()
    if not customer:
        return redirect(url_for('auth.customer_login'))
    return render_template('customer/profile.html', customer=customer)
