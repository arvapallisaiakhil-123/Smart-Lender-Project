import os
import datetime
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# We will initialize the client lazily to avoid DNS lookup errors on import/startup
_client = None

def get_db():
    """Lazily initialize the MongoDB client and return the database instance."""
    global _client

    if _client is None:
        dotenv_path = Path(__file__).parent / ".env"
        load_dotenv(dotenv_path=dotenv_path)

        mongo_uri = os.getenv("MONGO_URI")
        print("Mongo URI:", mongo_uri)

        if not mongo_uri:
            raise Exception("MONGO_URI not found in .env file")

        _client = MongoClient(mongo_uri)

    try:
        db = _client.get_database()

        # If no database name is present in the URI, use smart_lender
        if db.name == "test":
            db = _client["smart_lender"]

        return db

    except Exception:
        return _client["smart_lender"]

def create_database():
    """Ensure MongoDB collections and required indexes exist."""
    try:
        db = get_db()
        db.users.create_index("email", unique=True)
    except Exception as e:
        print(f"Error initializing indexes: {e}")

def create_users_table():
    """Wrapper function to align with existing app.py setup."""
    create_database()

def save_prediction(data):
    """Save prediction data tuple to predictions collection."""
    db = get_db()
    doc = {
        "applicant_name": data[0],
        "gender": data[1],
        "married": data[2],
        "dependents": data[3],
        "education": data[4],
        "self_employed": data[5],
        "applicant_income": data[6],
        "coapplicant_income": data[7],
        "loan_amount": data[8],
        "loan_term": data[9],
        "credit_history": data[10],
        "property_area": data[11],
        "prediction": data[12],
        "created_at": datetime.datetime.utcnow()
    }
    db.predictions.insert_one(doc)

def register_user(fullname, email, password):
    """Register a new user with hashed password."""
    db = get_db()
    hashed_password = generate_password_hash(password)
    doc = {
        "fullname": fullname,
        "email": email,
        "password": hashed_password,
        "created_at": datetime.datetime.utcnow()
    }
    try:
        db.users.insert_one(doc)
        return True
    except DuplicateKeyError:
        return False
    except Exception:
        return False

def login_user(email, password):
    """Authenticate user credentials."""
    db = get_db()
    user = db.users.find_one({"email": email})
    if user and check_password_hash(user.get("password", ""), password):
        return (str(user["_id"]), user.get("fullname"), user.get("email"), user.get("password"))
    return None

def get_predictions():
    """Get all predictions mapped to tuples for compatibility."""
    db = get_db()
    cursor = db.predictions.find().sort("_id", -1)
    results = []
    for doc in cursor:
        created_at = doc.get("created_at")
        if isinstance(created_at, datetime.datetime):
            created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
        else:
            created_at_str = str(created_at)
        results.append((
            str(doc.get("_id")),
            doc.get("applicant_name"),
            doc.get("gender"),
            doc.get("married"),
            doc.get("dependents"),
            doc.get("education"),
            doc.get("self_employed"),
            doc.get("applicant_income"),
            doc.get("coapplicant_income"),
            doc.get("loan_amount"),
            doc.get("loan_term"),
            doc.get("credit_history"),
            doc.get("property_area"),
            doc.get("prediction"),
            created_at_str
        ))
    return results

def get_all_predictions():
    """Get brief history of predictions format: (applicant_name, applicant_income, loan_amount, credit_history, prediction, created_at)"""
    db = get_db()
    cursor = db.predictions.find().sort("_id", -1)
    results = []
    for doc in cursor:
        created_at = doc.get("created_at")
        if isinstance(created_at, datetime.datetime):
            created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
        else:
            created_at_str = str(created_at)
        results.append((
            doc.get("applicant_name"),
            doc.get("applicant_income"),
            doc.get("loan_amount"),
            doc.get("credit_history"),
            doc.get("prediction"),
            created_at_str
        ))
    return results

def get_total_predictions():
    """Count total predictions."""
    db = get_db()
    return db.predictions.count_documents({})

def get_total_approved():
    """Count total approved predictions (contains 'Approved')."""
    db = get_db()
    return db.predictions.count_documents({"prediction": {"$regex": "Approved"}})

def get_total_rejected():
    """Count total rejected predictions (contains 'Rejected')."""
    db = get_db()
    return db.predictions.count_documents({"prediction": {"$regex": "Rejected"}})

def email_exists(email):
    """Check if email already exists."""
    db = get_db()
    user = db.users.find_one({"email": email})
    return user is not None

def get_user(user_id):
    """Retrieve user by ID."""
    db = get_db()
    from bson.objectid import ObjectId
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            return (str(user["_id"]), user.get("fullname"), user.get("email"))
    except Exception:
        pass
    return None