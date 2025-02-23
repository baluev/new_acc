import requests
from datetime import datetime
from models import db, Transaction, Account, Counteragent, TransactionGroup
from flask_login import current_user

class PlanFactAPI:
    BASE_URL = "https://api.planfact.io/api/v1"
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "X-ApiKey": api_key
        }
    
    def get_operations(self, limit=100, date_from=None):
        """Get operations from PlanFact API"""
        url = f"{self.BASE_URL}/operations"
        params = {
            "limit": limit
        }
        if date_from:
            params["dateFrom"] = date_from.strftime("%Y-%m-%d")
            
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

def get_or_create_group(category_data, operation_type, user_id):
    """Get or create a transaction group based on PlanFact category"""
    if not category_data or not category_data.get("title"):
        return None
        
    category_name = category_data["title"]
    if category_name == "Не выбран":
        return None
        
    group_type = "income" if operation_type == "Income" else "expense"
    
    group = TransactionGroup.query.filter_by(
        name=category_name,
        user_id=user_id,
        group_type=group_type
    ).first()
    
    if not group:
        group = TransactionGroup(
            name=category_name,
            group_type=group_type,
            user_id=user_id
        )
        db.session.add(group)
        db.session.commit()
    
    return group

def import_planfact_transactions(api_key, user_id=None):
    """Import transactions from PlanFact to our system"""
    api = PlanFactAPI(api_key)
    
    # Get last sync time
    if user_id:
        from models import ApiSettings
        settings = ApiSettings.query.filter_by(user_id=user_id).first()
        date_from = settings.last_sync_at if settings else None
    else:
        date_from = None
    
    # Get operations
    operations = api.get_operations(limit=100, date_from=date_from)
    
    imported_count = 0
    for operation in operations:
        # Skip if operation is not committed
        if not operation.get("isCommitted", False):
            continue
            
        # Get operation date
        operation_date = parse_datetime(operation["operationDate"])
        
        # Skip if we already have this transaction
        existing = Transaction.query.join(Account).filter(
            Transaction.datetime == operation_date,
            Account.user_id == (user_id or current_user.id),
            Transaction.amount == float(operation["value"]) * (-1 if operation["operationType"] == "Outcome" else 1)
        ).first()
        
        if existing:
            continue
            
        # Get or create account
        account_name = operation["account"]["title"]
        account_type = "income" if operation["operationType"] == "Income" else "expense"
        account = Account.query.filter_by(
            name=account_name, 
            user_id=user_id or current_user.id
        ).first()
        
        if not account:
            account = Account(
                name=account_name,
                account_type=account_type,
                user_id=user_id or current_user.id
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
                    user_id=user_id or current_user.id
                ).first()
                
                if not counteragent:
                    counteragent = Counteragent(
                        name=counteragent_name,
                        user_id=user_id or current_user.id
                    )
                    db.session.add(counteragent)
                    db.session.commit()
        
        # Get or create group based on operation category
        group = None
        if operation["operationParts"] and operation["operationParts"][0].get("operationCategory"):
            group = get_or_create_group(
                operation["operationParts"][0]["operationCategory"],
                operation["operationType"],
                user_id or current_user.id
            )
        
        # Parse dates
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
            group_id=group.id if group else None,
            comment=operation.get("comment", ""),
            created_at=create_date
        )
        
        db.session.add(transaction)
        imported_count += 1
    
    db.session.commit()
    return imported_count 