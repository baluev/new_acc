from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Account, Transaction
import os
from datetime import datetime, date
from calendar import month_name
from sqlalchemy import extract, func

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()  # This generates a secure random key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///company_finance.db'

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()  # Commit first to get the user.id
        
        # Now create a default account for the user
        default_account = Account(name='Main Account', user_id=user.id)
        db.session.add(default_account)
        db.session.commit()
        
        flash('Registration successful')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        
        flash('Invalid email or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    # Get current month's transactions
    today = date.today()
    transactions = Transaction.query\
        .join(Account)\
        .filter(
            Account.user_id == current_user.id,
            extract('year', Transaction.datetime) == today.year,
            extract('month', Transaction.datetime) == today.month
        )\
        .order_by(Transaction.datetime.desc())\
        .all()
    
    # Calculate total amount
    total_amount = db.session.query(func.sum(Transaction.amount))\
        .join(Account)\
        .filter(
            Account.user_id == current_user.id,
            extract('year', Transaction.datetime) == today.year,
            extract('month', Transaction.datetime) == today.month
        )\
        .scalar() or 0
    
    return render_template('index.html',
                         transactions=transactions,
                         total_amount=float(total_amount),
                         current_month_name=month_name[today.month])

@app.route('/transaction/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        account_id = request.form.get('account_id')
        amount = request.form.get('amount')
        counteragent = request.form.get('counteragent')
        comment = request.form.get('comment')
        
        # Verify account belongs to user
        account = Account.query.filter_by(id=account_id, user_id=current_user.id).first()
        if not account:
            flash('Invalid account')
            return redirect(url_for('add_transaction'))
        
        try:
            amount = float(amount)
            transaction = Transaction(
                account_id=account_id,
                amount=amount,
                counteragent=counteragent,
                comment=comment
            )
            db.session.add(transaction)
            db.session.commit()
            flash('Transaction added successfully')
            return redirect(url_for('index'))
        except ValueError:
            flash('Invalid amount')
            return redirect(url_for('add_transaction'))
    
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    return render_template('add_transaction.html', accounts=accounts)

@app.route('/transaction/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    transaction = Transaction.query.join(Account)\
        .filter(Transaction.id == id, Account.user_id == current_user.id)\
        .first_or_404()
    
    if request.method == 'POST':
        account_id = request.form.get('account_id')
        amount = request.form.get('amount')
        counteragent = request.form.get('counteragent')
        comment = request.form.get('comment')
        
        # Verify account belongs to user
        account = Account.query.filter_by(id=account_id, user_id=current_user.id).first()
        if not account:
            flash('Invalid account')
            return redirect(url_for('edit_transaction', id=id))
        
        try:
            transaction.account_id = account_id
            transaction.amount = float(amount)
            transaction.counteragent = counteragent
            transaction.comment = comment
            db.session.commit()
            flash('Transaction updated successfully')
            return redirect(url_for('index'))
        except ValueError:
            flash('Invalid amount')
            return redirect(url_for('edit_transaction', id=id))
    
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    return render_template('edit_transaction.html', transaction=transaction, accounts=accounts)

@app.route('/transaction/<int:id>/delete')
@login_required
def delete_transaction(id):
    transaction = Transaction.query.join(Account)\
        .filter(Transaction.id == id, Account.user_id == current_user.id)\
        .first_or_404()
    
    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted successfully')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 