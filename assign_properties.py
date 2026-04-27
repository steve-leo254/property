from dbservice import create_app, db, User, Property
import os

app = create_app()

with app.app_context():
    print("Assigning properties to regular user...")
    
    # Get the regular user (not admin)
    regular_user = User.query.filter_by(role='USER').first()
    admin_user = User.query.filter_by(role='ADMIN').first()
    
    if not regular_user:
        print("No regular user found!")
        exit()
    
    print(f"Regular user: {regular_user.username}")
    print(f"Admin user: {admin_user.username}")
    
    # Transfer 2 properties from admin to regular user
    admin_properties = Property.query.filter_by(owner_id=admin_user.id).limit(2).all()
    
    if admin_properties:
        for prop in admin_properties:
            prop.owner_id = regular_user.id
            print(f"Transferred: {prop.title}")
        
        db.session.commit()
        print("\nProperties transferred successfully!")
        
        # Show final counts
        regular_user_props = Property.query.filter_by(owner_id=regular_user.id).count()
        admin_user_props = Property.query.filter_by(owner_id=admin_user.id).count()
        
        print(f"\nFinal property counts:")
        print(f"Regular user ({regular_user.username}): {regular_user_props} properties")
        print(f"Admin user ({admin_user.username}): {admin_user_props} properties")
        
        # Show the properties
        print(f"\n{regular_user.username}'s properties:")
        for prop in Property.query.filter_by(owner_id=regular_user.id).all():
            print(f"  - {prop.title} (KSh {prop.price * 130:,.0f})")
    else:
        print("No properties found to transfer!")
