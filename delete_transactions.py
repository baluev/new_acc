from app import app, db
from models import Transaction

with app.app_context():
    Transaction.query.delete()
    db.session.commit()
    print('All transactions deleted successfully') 