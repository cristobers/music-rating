from main import app, db
import main

with app.app_context():
    print("creating database...")
    db.create_all()
    print("database created!")
