import requests
from datetime import datetime
from models import db, Transaction, Account, Counteragent
from flask_login import current_user

class PlanFactAPI:
    BASE_URL = "https://api.planfact.io/api/v1"
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "X-ApiKey": api_key
        }
    
    def get_operations(self, limit=10):
        """Get operations from PlanFact API"""
        url = f"{self.BASE_URL}/operations"
        params = {
            "limit": limit
        }
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            return response.json()["data"]["items"]
        else:
            raise Exception(f"Error getting operations: {response.status_code}")

def parse_datetime(date_str):
    """Parse datetime string from PlanFact API, handling different formats"""
    formats = [
        '%Y-%m-%dT%H:%M:%S.%f',  # With microseconds
        '%Y-%m-%dT%H:%M:%S',     # Without microseconds
        '%Y-%m-%d'               # Just date
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Time data '{date_str}' does not match any expected format")

def import_planfact_transactions(api_key):
    """Import transactions from PlanFact to our system"""
    api = PlanFactAPI(api_key)
    operations = api.get_operations()
    
    imported_count = 0
    for operation in operations:
        # Skip if operation is not committed
        if not operation.get("isCommitted", False):
            continue
            
        # Get or create account
        account_name = operation["account"]["title"]
        account_type = "income" if operation["operationType"] == "Income" else "expense"
        account = Account.query.filter_by(
            name=account_name, 
            user_id=current_user.id
        ).first()
        
        if not account:
            account = Account(
                name=account_name,
                account_type=account_type,
                user_id=current_user.id
            )
            db.session.add(account)
            db.session.commit()
        
        # Get or create counteragent if exists
        counteragent = None
        if operation["operationParts"] and operation["operationParts"][0].get("contrAgent"):
            counteragent_name = operation["operationParts"][0]["contrAgent"]["title"]
            if counteragent_name != "Не выбран":
                counteragent = Counteragent.query.filter_by(
                    name=counteragent_name,
                    user_id=current_user.id
                ).first()
                
                if not counteragent:
                    counteragent = Counteragent(
                        name=counteragent_name,
                        user_id=current_user.id
                    )
                    db.session.add(counteragent)
                    db.session.commit()
        
        # Parse dates
        operation_date = parse_datetime(operation["operationDate"])
        create_date = parse_datetime(operation["createDate"])
        
        # Create transaction
        amount = float(operation["value"])
        if operation["operationType"] == "Outcome":
            amount = -amount
            
        transaction = Transaction(
            datetime=operation_date,
            account_id=account.id,
            amount=amount,
            counteragent_id=counteragent.id if counteragent else None,
            comment=operation.get("comment", ""),
            created_at=create_date
        )
        
        db.session.add(transaction)
        imported_count += 1
    
    db.session.commit()
    return imported_count 