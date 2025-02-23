from datetime import datetime, timedelta
import time
import threading

def sync_transactions(app, db):
    """Background task to sync transactions from PlanFact"""
    from models import ApiSettings
    from planfact_import import import_planfact_transactions
    
    while True:
        with app.app_context():
            try:
                # Get all API settings
                settings = ApiSettings.query.all()
                
                for setting in settings:
                    try:
                        # Check if we need to sync (every 2 minutes)
                        if (not setting.last_sync_at or 
                            datetime.utcnow() - setting.last_sync_at > timedelta(minutes=2)):
                            
                            # Import transactions
                            import_planfact_transactions(setting.api_key, user_id=setting.user_id)
                            
                            # Update last sync time
                            setting.last_sync_at = datetime.utcnow()
                            db.session.commit()
                            
                            print(f"Synced transactions for user {setting.user_id}")
                            
                    except Exception as e:
                        print(f"Error syncing transactions for user {setting.user_id}: {str(e)}")
                        continue
                        
            except Exception as e:
                print(f"Error in sync task: {str(e)}")
            
            # Sleep for 2 minutes before next check
            time.sleep(120)

def start_sync_thread(app, db):
    """Start the background sync thread"""
    thread = threading.Thread(target=sync_transactions, args=(app, db), daemon=True)
    thread.start()
    return thread 