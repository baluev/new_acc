from app import app, db
from models import User, Transaction, TransactionGroup, Account, Counteragent

def print_stats():
    """Print statistics about imported data"""
    with app.app_context():
        user = User.query.filter_by(email="test@example.com").first()
        if not user:
            print("Test user not found!")
            return
            
        transactions = Transaction.query.filter(
            Transaction.account_id.in_(
                Account.query.filter_by(user_id=user.id).with_entities(Account.id)
            )
        ).all()
        
        groups = TransactionGroup.query.filter_by(user_id=user.id).all()
        accounts = Account.query.filter_by(user_id=user.id).all()
        counteragents = Counteragent.query.filter_by(user_id=user.id).all()
        
        print(f"\nImport Statistics:")
        print(f"Total transactions: {len(transactions)}")
        print(f"Total groups: {len(groups)}")
        print(f"Total accounts: {len(accounts)}")
        print(f"Total counteragents: {len(counteragents)}")
        
        print("\nGroups:")
        for group in groups:
            group_transactions = [t for t in transactions if t.group_id == group.id]
            print(f"- {group.name} ({group.group_type}): {len(group_transactions)} transactions")
            
        print("\nAccounts:")
        for account in accounts:
            account_transactions = [t for t in transactions if t.account_id == account.id]
            print(f"- {account.name} ({account.account_type}): {len(account_transactions)} transactions")

if __name__ == "__main__":
    print_stats() 