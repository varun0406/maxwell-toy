import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import User
from app.auth import hash_password

def set_superuser(username, pin):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"User '{username}' not found. Creating as superuser...")
            user = User(username=username, is_superuser=True)
            db.add(user)
        else:
            print(f"User '{username}' found. Updating PIN and ensuring superuser status...")
            user.is_superuser = True
            
        user.hashed_password = hash_password(pin)
        db.commit()
        print(f"Successfully set PIN for superuser '{username}'.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Set superuser PIN")
    parser.add_argument("--username", default="raju", help="Username of the superuser")
    parser.add_argument("--pin", required=True, help="The new 4+ digit PIN")
    args = parser.parse_args()
    
    set_superuser(args.username, args.pin)
