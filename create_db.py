from app import app, db
from models import User, Account, Counteragent, Transaction, TransactionGroup

with app.app_context():
    db.drop_all()
    db.create_all()
    print("Database tables created successfully") 