from app import app, db
from models import User
from planfact_import import import_planfact_transactions

API_KEY = "JlUMUlFiOHg2UZh7qOGqwTnN8IrTyqELJiJoO7-2A8g9d4aD8PEDw_hFtMYDz0tXKJhxDym4mNcmagoIowiIEcfGvZBS5dVjLlVPU9YQJ4ucC3_knT3uxNaM8N9a2i6eVxaoXI-0ik64etVOcnRo0w7u3PufHuJKbr6uMAFUMQQVfoztLxU5WxG-U_fjXtBoQCbx7RVXfMSmRsIj3N80vkKcLhCBsOVLOSVu219eAIgYWfvl6nUE3V0YjH6Wr-Bm11SAMo67MMPG1VDwHOdE9LPFanT6HeQSXlKERFVlve__5lnH8SB7ocaQbtrlnpgXomL9IkmNia-P-J9uw-ukKMPUVxvxtfuQTblLR4y1YrF-BK5HU7wgF7g2qKhiKxdgehimXjpbU9Fy2p9dhsP-A2HScGWc5QV9FTXcCL0cX-RwPY31q9N_kahvTkyayjTOXr37NkeHkHw-4ok_SvDqBXphKPWHGsC4CVfyA7AmnwAKb_RJMtxi_gw0GUJy3iwqXXYprVePkuKygCAOkBU9nkfLrQZO2sRDFPYZbgyOQgzjpw75r6WvOpeakTq2GPtn2E3GglBrOcm3SojSyMlp0oKuSbw"

with app.app_context():
    # Create test user if not exists
    user = User.query.filter_by(email="test@example.com").first()
    if not user:
        user = User(email="test@example.com")
        user.set_password("test123")
        db.session.add(user)
        db.session.commit()
        print("Created test user")
    
    # Import transactions with user_id
    imported_count = import_planfact_transactions(API_KEY, user_id=user.id)
    print(f"Successfully imported {imported_count} transactions") 