"""
Customer forms for City Printers CRM.
Used by cashier for create/edit/search; admin view-only uses list/detail.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError


def _email_unique(form, field):
    """Validate email is unique (used in create; for edit, exclude current customer via form._obj)."""
    from app.models.customer import Customer
    q = Customer.query.filter(Customer.email == field.data.strip().lower())
    if getattr(form, '_obj', None):
        q = q.filter(Customer.id != form._obj.id)
    if q.first():
        raise ValidationError('A customer with this email already exists.')


def _phone_unique(form, field):
    """Validate phone is unique when provided (enforced)."""
    val = (field.data or '').strip()
    if not val:
        return
    from app.models.customer import Customer
    q = Customer.query.filter(Customer.phone_number == val)
    if getattr(form, '_obj', None):
        q = q.filter(Customer.id != form._obj.id)
    if q.first():
        raise ValidationError('A customer with this phone number already exists.')


class CustomerCreateForm(FlaskForm):
    """Form for cashier to register a new customer. All key fields required."""
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=80)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=80)])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(max=20)], description='Required')
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120), _email_unique])
    address = StringField('Address', validators=[Optional(), Length(max=255)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)], description='For customer portal login')
    password_confirm = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Register Customer')


class CustomerEditForm(FlaskForm):
    """Form for cashier to edit customer. Password optional (change only if filled)."""
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=80)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=80)])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120), _email_unique])
    address = StringField('Address', validators=[Optional(), Length(max=255)])
    password = PasswordField('New Password', validators=[Optional(), Length(min=6)], description='Leave blank to keep current')
    password_confirm = PasswordField('Confirm New Password', validators=[
        Optional(),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Save Changes')


class CustomerSearchForm(FlaskForm):
    """Search customers by name, phone, or email. Optional query."""
    q = StringField('Search', validators=[Optional(), Length(max=120)], description='Name, phone, or email')
    submit = SubmitField('Search')
