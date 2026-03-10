"""
Cashier blueprint: dashboard, customer management, and (later) orders, payment, receipt.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.routes.decorators import cashier_required
from app import db
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.receipt import Receipt
from app.models.service import Service
from app.forms.customer_forms import CustomerCreateForm, CustomerEditForm, CustomerSearchForm
from app.forms.order_forms import OrderCreateForm
from app.forms.payment_forms import PaymentForm
from datetime import date, datetime
from decimal import Decimal
from flask_login import current_user

cashier_bp = Blueprint('cashier', __name__)


def _search_customers(query):
    """Search customers by name, phone, or email. Returns base query. Case-insensitive."""
    if not (query and query.strip()):
        return Customer.query.order_by(Customer.last_name, Customer.first_name)
    q = query.strip()
    term = f'%{q}%'
    # Use lower() for case-insensitive search on both MySQL and SQLite
    return Customer.query.filter(
        db.or_(
            db.func.lower(Customer.first_name).like(db.func.lower(term)),
            db.func.lower(Customer.last_name).like(db.func.lower(term)),
            db.func.lower(Customer.email).like(db.func.lower(term)),
            Customer.phone_number.like(term),
        )
    ).order_by(Customer.last_name, Customer.first_name)


@cashier_bp.route('/')
@cashier_bp.route('/dashboard')
@cashier_required
def dashboard():
    """
    Cashier dashboard: today's stats and recent activity.
    """
    orders_today = Order.query.filter(db.func.date(Order.order_date) == date.today()).count()

    from app.models.payment import Payment
    revenue_today = db.session.query(db.func.coalesce(db.func.sum(Payment.amount_paid), 0)).join(
        Order
    ).filter(db.func.date(Order.order_date) == date.today()).scalar() or 0

    orders_in_progress = Order.query.filter_by(order_status=Order.STATUS_IN_PROGRESS).count()
    completed = Order.query.filter(
        Order.order_status.in_([Order.STATUS_COMPLETED, Order.STATUS_COLLECTED])
    ).count()

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    recent_customers = Customer.query.order_by(Customer.created_at.desc()).limit(10).all()

    return render_template(
        'cashier/dashboard.html',
        orders_today=orders_today,
        revenue_today=revenue_today,
        orders_in_progress=orders_in_progress,
        completed_jobs=completed,
        recent_orders=recent_orders,
        recent_customers=recent_customers,
    )


# --- Customer Management (cashier: full CRUD) ---


@cashier_bp.route('/customers')
@cashier_required
def customer_list():
    """List all customers with optional search by name, phone, or email."""
    form = CustomerSearchForm()
    q = request.args.get('q', '').strip()
    if q:
        form.q.data = q
    customers = _search_customers(q).all()
    return render_template('cashier/customers/list.html', customers=customers, form=form)


@cashier_bp.route('/customers/create', methods=['GET', 'POST'])
@cashier_required
def customer_create():
    """Register a new customer. Sets password for portal login."""
    form = CustomerCreateForm()
    if form.validate_on_submit():
        customer = Customer(
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            phone_number=form.phone_number.data.strip(),
            email=form.email.data.strip().lower(),
            address=form.address.data.strip() or None,
        )
        customer.set_password(form.password.data)
        db.session.add(customer)
        db.session.commit()
        flash(f'Customer {customer.full_name} registered successfully.', 'success')
        return redirect(url_for('cashier.customer_detail', customer_id=customer.id))
    return render_template('cashier/customers/create.html', form=form)


@cashier_bp.route('/customers/<int:customer_id>')
@cashier_required
def customer_detail(customer_id):
    """View customer details and their orders."""
    customer = Customer.query.get_or_404(customer_id)
    orders = customer.orders.order_by(Order.created_at.desc()).limit(20).all()
    return render_template('cashier/customers/detail.html', customer=customer, orders=orders)


@cashier_bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@cashier_required
def customer_edit(customer_id):
    """Edit customer details. Optional password change."""
    customer = Customer.query.get_or_404(customer_id)
    form = CustomerEditForm(obj=customer)
    form._obj = customer  # for unique validators (exclude self)
    if form.validate_on_submit():
        customer.first_name = form.first_name.data.strip()
        customer.last_name = form.last_name.data.strip()
        customer.phone_number = form.phone_number.data.strip()
        customer.email = form.email.data.strip().lower()
        customer.address = form.address.data.strip() or None
        if form.password.data:
            customer.set_password(form.password.data)
        db.session.commit()
        flash(f'Customer {customer.full_name} updated successfully.', 'success')
        return redirect(url_for('cashier.customer_detail', customer_id=customer.id))
    return render_template('cashier/customers/edit.html', form=form, customer=customer)


# --- Order Management (cashier: list, create, detail) ---


@cashier_bp.route('/orders')
@cashier_required
def order_list():
    """List all service orders (newest first)."""
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('cashier/orders/list.html', orders=orders)


@cashier_bp.route('/orders/create', methods=['GET', 'POST'])
@cashier_required
def order_create():
    """Create a new order for an existing customer with one or more service items."""
    form = OrderCreateForm()
    # Choices: customers and active services
    form.customer_id.choices = [
        (c.id, c.full_name) for c in Customer.query.order_by(Customer.last_name, Customer.first_name).all()
    ]
    if not form.customer_id.choices:
        flash('Register at least one customer before creating an order.', 'warning')
        return redirect(url_for('cashier.customer_list'))
    active_services = Service.get_active_services()
    service_choices = [('', '-- Select service --')] + [(s.id, f'{s.service_name} — R{s.unit_price:.2f}') for s in active_services]
    if len(service_choices) == 1:
        flash('Add at least one active service (Admin → Services) before creating an order.', 'warning')
        return redirect(url_for('cashier.order_list'))
    for item in form.items:
        item.service_id.choices = service_choices

    if form.validate_on_submit():
        customer_id = form.customer_id.data
        order = Order(
            customer_id=customer_id,
            created_by=current_user.id,
            order_date=date.today(),
            total_amount=Decimal('0.00'),
            order_status=Order.STATUS_PENDING,
        )
        db.session.add(order)
        db.session.flush()  # get order.id
        total = Decimal('0.00')
        for entry in form.items:
            try:
                sid = int(entry.service_id.data) if entry.service_id.data else None
            except (TypeError, ValueError):
                sid = None
            qty = entry.quantity.data
            if sid is None or qty is None or qty < 1:
                continue
            service = Service.query.get(sid)
            if not service or not service.active_status:
                continue
            unit_price = service.unit_price
            subtotal = Decimal(str(qty)) * unit_price
            total += subtotal
            item = OrderItem(
                order_id=order.id,
                service_id=sid,
                quantity=qty,
                unit_price=unit_price,
                subtotal=subtotal,
            )
            db.session.add(item)
        order.total_amount = total
        db.session.commit()
        flash(f'Order #{order.id} created successfully. Total: R{order.total_amount:.2f}', 'success')
        return redirect(url_for('cashier.order_detail', order_id=order.id))
    return render_template('cashier/orders/create.html', form=form)


@cashier_bp.route('/orders/<int:order_id>')
@cashier_required
def order_detail(order_id):
    """View order details: customer, items, total, status. Shows Paid/Unpaid and payment/receipt actions."""
    order = Order.query.get_or_404(order_id)
    return render_template('cashier/orders/detail.html', order=order)


def _generate_receipt_number(order_id):
    """Generate unique receipt number: RCP-<order_id>-<YYYYMMDD>."""
    return f'RCP-{order_id}-{datetime.utcnow().strftime("%Y%m%d")}'


def _create_receipt_for_order(order):
    """
    Create and persist one receipt for the order (after payment).
    Called only when order has a payment and no receipt yet.
    """
    receipt_number = _generate_receipt_number(order.id)
    receipt = Receipt(order_id=order.id, receipt_number=receipt_number)
    db.session.add(receipt)
    db.session.flush()
    return receipt


# --- Payment and Receipt (cashier) ---


@cashier_bp.route('/orders/<int:order_id>/payment', methods=['GET', 'POST'])
@cashier_required
def order_payment(order_id):
    """
    Record full payment for an order. One payment per order.
    If order already has payment, redirect to order detail with warning.
    On success: create Payment, then create Receipt, redirect to receipt view.
    """
    order = Order.query.get_or_404(order_id)
    if order.payment:
        flash('This order already has a payment recorded.', 'warning')
        return redirect(url_for('cashier.order_detail', order_id=order.id))

    form = PaymentForm()
    # Pre-fill amount with order total (read-only in template)
    form.amount_paid.data = float(order.total_amount)

    if form.validate_on_submit():
        amount_submitted = Decimal(str(form.amount_paid.data))
        if amount_submitted != order.total_amount:
            flash(f'Amount paid must equal order total (R {order.total_amount:.2f}). Partial payment is not allowed.', 'danger')
            return render_template('cashier/orders/payment.html', order=order, form=form)

        payment = Payment(
            order_id=order.id,
            amount_paid=amount_submitted,
            payment_method=form.payment_method.data,
            recorded_by=current_user.id,
        )
        db.session.add(payment)
        db.session.flush()
        # Generate receipt after payment
        _create_receipt_for_order(order)
        db.session.commit()
        flash(f'Payment of R {payment.amount_paid:.2f} recorded. Receipt generated.', 'success')
        return redirect(url_for('cashier.order_receipt', order_id=order.id))

    return render_template('cashier/orders/payment.html', order=order, form=form)


@cashier_bp.route('/orders/<int:order_id>/receipt')
@cashier_required
def order_receipt(order_id):
    """View/print receipt for a paid order. Requires order to have payment and receipt."""
    order = Order.query.get_or_404(order_id)
    if not order.payment:
        flash('Record payment first to generate a receipt.', 'warning')
        return redirect(url_for('cashier.order_detail', order_id=order.id))
    if not order.receipt:
        flash('Receipt not found. Please contact support.', 'warning')
        return redirect(url_for('cashier.order_detail', order_id=order.id))
    return render_template(
        'cashier/orders/receipt.html',
        order=order,
        payment=order.payment,
        receipt=order.receipt,
    )
