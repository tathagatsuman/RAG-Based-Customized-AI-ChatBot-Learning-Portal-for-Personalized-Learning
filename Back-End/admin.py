from app import db, User, app

def create_admin():
    with app.app_context():
        email = "admin@admin.com"
        password = "Admin@123"
        name = "ADMIN"
        role = "admin"
        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print("Admin-User created successfully...")
        
if __name__ == '__main__':
    create_admin()

