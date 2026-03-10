"""
Staff/Admin user model for City Printers CRM.
Roles: admin, cashier.
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login. Staff only (User model)."""
    from app.models.user import User
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    """
    Staff user: Admin or Cashier.
    Used for Flask-Login (staff login).
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'cashier'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Orders created by this staff member
    orders_created = db.relationship(
        'Order',
        backref='created_by_user',
        foreign_keys='Order.created_by',
        lazy='dynamic'
    )

    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_cashier(self):
        return self.role == 'cashier'

    def __repr__(self):
        return f'<User {self.email}>'
