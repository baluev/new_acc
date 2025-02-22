from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from models import db, User, Account, Transaction, Counteragent
import os
from datetime import datetime, date
from calendar import month_name
from sqlalchemy import extract, func

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()  # This generates a secure random key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///company_finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Template filters
@app.template_filter('abs')
def abs_filter(number):
    return abs(float(number))

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
        
        # Create default accounts for the user
        default_income = Account(name='Main Income', account_type='income', user_id=user.id)
        default_expense = Account(name='Main Expense', account_type='expense', user_id=user.id)
        db.session.add(default_income)
        db.session.add(default_expense)
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

@app.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    income_accounts = Account.query.filter_by(user_id=current_user.id, account_type='income').all()
    expense_accounts = Account.query.filter_by(user_id=current_user.id, account_type='expense').all()
    counteragents = Counteragent.query.filter_by(user_id=current_user.id).all()
    
    if request.method == 'POST':
        account_id = request.form.get('account_id')
        amount = request.form.get('amount')
        counteragent_id = request.form.get('counteragent_id')
        comment = request.form.get('comment')
        
        if not account_id or not amount:
            flash('Account and amount are required')
            return redirect(url_for('add_transaction'))
        
        # Create transaction
        transaction = Transaction(
            account_id=account_id,
            amount=amount,
            counteragent_id=counteragent_id if counteragent_id else None,
            comment=comment
        )
        
        db.session.add(transaction)
        db.session.commit()
        flash('Transaction added successfully')
        return redirect(url_for('index'))
    
    return render_template('add_transaction.html', 
                         income_accounts=income_accounts,
                         expense_accounts=expense_accounts,
                         counteragents=counteragents)

@app.route('/transactions/<int:transaction_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.join(Account).filter(
        Transaction.id == transaction_id,
        Account.user_id == current_user.id
    ).first_or_404()
    
    income_accounts = Account.query.filter_by(user_id=current_user.id, account_type='income').all()
    expense_accounts = Account.query.filter_by(user_id=current_user.id, account_type='expense').all()
    counteragents = Counteragent.query.filter_by(user_id=current_user.id).all()
    
    if request.method == 'POST':
        account_id = request.form.get('account_id')
        amount = request.form.get('amount')
        counteragent_id = request.form.get('counteragent_id')
        comment = request.form.get('comment')
        
        if not account_id or not amount:
            flash('Account and amount are required')
            return redirect(url_for('edit_transaction', transaction_id=transaction_id))
        
        # Update transaction
        transaction.account_id = account_id
        transaction.amount = amount
        transaction.counteragent_id = counteragent_id if counteragent_id else None
        transaction.comment = comment
        
        db.session.commit()
        flash('Transaction updated successfully')
        return redirect(url_for('index'))
    
    return render_template('edit_transaction.html', 
                         transaction=transaction, 
                         income_accounts=income_accounts,
                         expense_accounts=expense_accounts,
                         counteragents=counteragents)

@app.route('/transaction/<int:transaction_id>/delete')
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.join(Account)\
        .filter(Transaction.id == transaction_id, Account.user_id == current_user.id)\
        .first_or_404()
    
    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted successfully')
    return redirect(url_for('index'))

@app.route('/accounts')
@login_required
def accounts():
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    # Calculate balance for each account
    for account in accounts:
        balance = db.session.query(func.sum(Transaction.amount)).filter_by(account_id=account.id).scalar() or 0
        account.balance = float(balance)
    return render_template('accounts.html', accounts=accounts)

@app.route('/accounts/add', methods=['GET', 'POST'])
@login_required
def add_account():
    if request.method == 'POST':
        name = request.form.get('name')
        account_type = request.form.get('account_type')
        
        if not name or not account_type:
            flash('Account name and type are required')
            return redirect(url_for('add_account'))
        
        if account_type not in ['income', 'expense']:
            flash('Invalid account type')
            return redirect(url_for('add_account'))
        
        account = Account(name=name, account_type=account_type, user_id=current_user.id)
        db.session.add(account)
        db.session.commit()
        flash('Account added successfully')
        return redirect(url_for('accounts'))
    
    return render_template('add_account.html')

@app.route('/accounts/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_account(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        name = request.form.get('name')
        account_type = request.form.get('account_type')
        
        if not name or not account_type:
            flash('Account name and type are required')
            return redirect(url_for('edit_account', account_id=account_id))
        
        if account_type not in ['income', 'expense']:
            flash('Invalid account type')
            return redirect(url_for('edit_account', account_id=account_id))
        
        account.name = name
        account.account_type = account_type
        db.session.commit()
        flash('Account updated successfully')
        return redirect(url_for('accounts'))
    
    return render_template('edit_account.html', account=account)

@app.route('/accounts/<int:account_id>/delete')
@login_required
def delete_account(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    
    # Check if account has transactions
    if account.transactions:
        flash('Cannot delete account with transactions')
        return redirect(url_for('accounts'))
    
    db.session.delete(account)
    db.session.commit()
    flash('Account deleted successfully')
    return redirect(url_for('accounts'))

@app.route('/counteragents')
@login_required
def counteragents():
    counteragents = Counteragent.query.filter_by(user_id=current_user.id).all()
    return render_template('counteragents.html', counteragents=counteragents)

@app.route('/counteragents/add', methods=['GET', 'POST'])
@login_required
def add_counteragent():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Counteragent name is required')
            return redirect(url_for('add_counteragent'))
        
        counteragent = Counteragent(name=name, description=description, user_id=current_user.id)
        db.session.add(counteragent)
        db.session.commit()
        flash('Counteragent added successfully')
        return redirect(url_for('counteragents'))
    
    return render_template('add_counteragent.html')

@app.route('/counteragents/<int:counteragent_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_counteragent(counteragent_id):
    counteragent = Counteragent.query.filter_by(id=counteragent_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Counteragent name is required')
            return redirect(url_for('edit_counteragent', counteragent_id=counteragent_id))
        
        counteragent.name = name
        counteragent.description = description
        db.session.commit()
        flash('Counteragent updated successfully')
        return redirect(url_for('counteragents'))
    
    return render_template('edit_counteragent.html', counteragent=counteragent)

@app.route('/counteragents/<int:counteragent_id>/delete')
@login_required
def delete_counteragent(counteragent_id):
    counteragent = Counteragent.query.filter_by(id=counteragent_id, user_id=current_user.id).first_or_404()
    
    # Check if counteragent has transactions
    if counteragent.transactions:
        flash('Cannot delete counteragent with transactions')
        return redirect(url_for('counteragents'))
    
    db.session.delete(counteragent)
    db.session.commit()
    flash('Counteragent deleted successfully')
    return redirect(url_for('counteragents'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 