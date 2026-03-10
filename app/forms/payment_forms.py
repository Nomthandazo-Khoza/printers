"""
Payment forms for City Printers CRM.
Full payment only; amount must equal order total (validated in view).
"""
from flask_wtf import FlaskForm
from wtforms import SelectField, FloatField, SubmitField
from wtforms.validators import DataRequired, NumberRange


# Allowed payment methods (business rule)
PAYMENT_METHODS = [
    ('Cash', 'Cash'),
    ('Card', 'Card'),
    ('EFT', 'EFT'),
    ('Mobile', 'Mobile'),
]


class PaymentForm(FlaskForm):
    """
    Record full payment for an order.
    - payment_method: required, one of Cash/Card/EFT/Mobile.
    - amount_paid: required, must equal order.total_amount (enforced in view).
    """
    payment_method = SelectField(
        'Payment Method',
        choices=PAYMENT_METHODS,
        validators=[DataRequired(message='Select a payment method.')]
    )
    amount_paid = FloatField(
        'Amount Paid (R)',
        validators=[
            DataRequired(message='Amount is required.'),
            NumberRange(min=0.01, message='Amount must be greater than 0.')
        ],
        render_kw={'readonly': True, 'step': '0.01'}
    )
    submit = SubmitField('Record Payment')
