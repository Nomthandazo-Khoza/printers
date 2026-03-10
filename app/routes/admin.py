"""
Admin blueprint: dashboard, customer view, service management, (later) user/order/reports.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.routes.decorators import admin_required
from app import db
from app.models.user import User
from app.models.customer import Customer
from app.models.order import Order
from app.models.service import Service
from app.forms.customer_forms import CustomerSearchForm
from app.forms.service_forms import ServiceForm
from datetime import datetime, date
from decimal import Decimal

admin_bp = Blueprint('admin', __name__)


def _search_customers(query):
    """Search customers by name, phone, or email. Returns base query. Case-insensitive."""
    if not (query and query.strip()):
        return Customer.query.order_by(Customer.last_name, Customer.first_name)
    q = query.strip()
    term = f'%{q}%'
    return Customer.query.filter(
        db.or_(
            db.func.lower(Customer.first_name).like(db.func.lower(term)),
            db.func.lower(Customer.last_name).like(db.func.lower(term)),
            db.func.lower(Customer.email).like(db.func.lower(term)),
            Customer.phone_number.like(term),
        )
    ).order_by(Customer.last_name, Customer.first_name)


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """
    Admin dashboard: totals, today's stats, recent orders, recent customers.
    """
    # Counts
    total_customers = Customer.query.count()
    orders_today = Order.query.filter(db.func.date(Order.order_date) == date.today()).count()
    orders_in_progress = Order.query.filter_by(order_status=Order.STATUS_IN_PROGRESS).count()
    completed = Order.query.filter(
        Order.order_status.in_([Order.STATUS_COMPLETED, Order.STATUS_COLLECTED])
    ).count()

    # Revenue today (from payments for orders with order_date today)
    from app.models.payment import Payment
    revenue_today = db.session.query(db.func.coalesce(db.func.sum(Payment.amount_paid), 0)).join(
        Order
    ).filter(db.func.date(Order.order_date) == date.today()).scalar() or 0

    # Recent orders (last 10)
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    recent_customers = Customer.query.order_by(Customer.created_at.desc()).limit(10).all()

    return render_template(
        'admin/dashboard.html',
        total_customers=total_customers,
        orders_today=orders_today,
        revenue_today=revenue_today,
        orders_in_progress=orders_in_progress,
        completed_jobs=completed,
        recent_orders=recent_orders,
        recent_customers=recent_customers,
    )


# --- Customer Management (admin: view only - list and detail) ---


@admin_bp.route('/customers')
@admin_required
def customer_list():
    """List all customers with optional search."""
    form = CustomerSearchForm()
    q = request.args.get('q', '').strip()
    if q:
        form.q.data = q
    customers = _search_customers(q).all()
    return render_template('admin/customers/list.html', customers=customers, form=form)


@admin_bp.route('/customers/<int:customer_id>')
@admin_required
def customer_detail(customer_id):
    """View customer details (read-only)."""
    customer = Customer.query.get_or_404(customer_id)
    orders = customer.orders.order_by(Order.created_at.desc()).limit(20).all()
    return render_template('admin/customers/detail.html', customer=customer, orders=orders)


# --- Service Management (admin only: list, create, edit, activate/deactivate) ---


@admin_bp.route('/services')
@admin_required
def service_list():
    """List all services (active and inactive)."""
    services = Service.query.order_by(Service.service_name).all()
    return render_template('admin/services/list.html', services=services)


@admin_bp.route('/services/create', methods=['GET', 'POST'])
@admin_required
def service_create():
    """Add a new service."""
    form = ServiceForm()
    if form.validate_on_submit():
        service = Service(
            service_name=form.service_name.data.strip(),
            description=form.description.data.strip() or None,
            unit_price=Decimal(str(form.unit_price.data)),
            active_status=form.active_status.data,
        )
        db.session.add(service)
        db.session.commit()
        flash(f'Service "{service.service_name}" added successfully.', 'success')
        return redirect(url_for('admin.service_list'))
    return render_template('admin/services/create.html', form=form)


@admin_bp.route('/services/<int:service_id>/edit', methods=['GET', 'POST'])
@admin_required
def service_edit(service_id):
    """Edit service details and activate/deactivate."""
    service = Service.query.get_or_404(service_id)
    form = ServiceForm(obj=service)
    form._obj = service  # for unique name validator
    # Coerce Decimal to float for form
    if request.method == 'GET':
        form.unit_price.data = float(service.unit_price)
    if form.validate_on_submit():
        service.service_name = form.service_name.data.strip()
        service.description = form.description.data.strip() or None
        service.unit_price = Decimal(str(form.unit_price.data))
        service.active_status = form.active_status.data
        db.session.commit()
        flash(f'Service "{service.service_name}" updated successfully.', 'success')
        return redirect(url_for('admin.service_list'))
    return render_template('admin/services/edit.html', form=form, service=service)


@admin_bp.route('/services/<int:service_id>/toggle-status', methods=['POST'])
@admin_required
def service_toggle_status(service_id):
    """Activate or deactivate a service (quick toggle from list)."""
    service = Service.query.get_or_404(service_id)
    service.active_status = not service.active_status
    db.session.commit()
    status = 'activated' if service.active_status else 'deactivated'
    flash(f'Service "{service.service_name}" {status}.', 'success')
    return redirect(url_for('admin.service_list'))


# --- Order Management (admin: view only - list and detail) ---


@admin_bp.route('/orders')
@admin_required
def order_list():
    """List all service orders (newest first)."""
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders/list.html', orders=orders)


@admin_bp.route('/orders/<int:order_id>')
@admin_required
def order_detail(order_id):
    """View order details (read-only): customer, items, total, status. Shows Paid/Unpaid and View Receipt if paid."""
    order = Order.query.get_or_404(order_id)
    return render_template('admin/orders/detail.html', order=order)


@admin_bp.route('/orders/<int:order_id>/receipt')
@admin_required
def order_receipt(order_id):
    """View/print receipt for a paid order (read-only)."""
    order = Order.query.get_or_404(order_id)
    if not order.payment:
        flash('No payment recorded for this order.', 'warning')
        return redirect(url_for('admin.order_detail', order_id=order.id))
    if not order.receipt:
        flash('Receipt not found for this order.', 'warning')
        return redirect(url_for('admin.order_detail', order_id=order.id))
    return render_template(
        'admin/orders/receipt.html',
        order=order,
        payment=order.payment,
        receipt=order.receipt,
    )
