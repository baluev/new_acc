from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.sql import func

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    accounts = db.relationship('Account', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(20), nullable=False, default='expense')  # 'income' or 'expense'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transactions = db.relationship('Transaction', backref='account', lazy=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())

    def __repr__(self):
        return f'<Account {self.name} ({self.account_type})>'

class Counteragent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())
    transactions = db.relationship('Transaction', backref='counteragent_ref', lazy=True)

    def __repr__(self):
        return f'<Counteragent {self.name}>'

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False, server_default=func.now())
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)  # Using Numeric for precise decimal calculations
    counteragent_id = db.Column(db.Integer, db.ForeignKey('counteragent.id'))
    counteragent = db.Column(db.String(200))  # For backward compatibility and optional counteragents
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())

    def __repr__(self):
        return f'<Transaction {self.datetime}: {self.amount}>' 