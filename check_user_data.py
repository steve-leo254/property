from dbservice import create_app, db, User, Property, Inquiry, PropertyType, Location, UserRole, ListingType, PropertyStatus
import os

app = create_app()

with app.app_context():
    print("Checking current user data...")
    
    # Get current users
    users = User.query.all()
    print(f"Total users: {len(users)}")
    
    for user in users:
        print(f"\nUser: {user.username} | Email: {user.email} | Role: {user.role}")
        
        # Check user's properties
        my_properties = Property.query.filter_by(owner_id=user.id).all()
        print(f"  Properties owned: {len(my_properties)}")
        
        # Check user's inquiries
        my_inquiries = Inquiry.query.filter_by(user_id=user.id).all()
        print(f"  Inquiries made: {len(my_inquiries)}")
        
        # Show details if any exist
        if my_properties:
            for prop in my_properties:
                print(f"    - {prop.title} (KSh {prop.price * 130:,.0f})")
        
        if my_inquiries:
            for inquiry in my_inquiries:
                print(f"    - Inquiry for: {inquiry.property.title} on {inquiry.created_at.strftime('%Y-%m-%d')}")
    
    # If no user has properties, let's assign some to the first user
    if users and not any(Property.query.filter_by(owner_id=user.id).count() > 0 for user in users):
        print("\n\nNo user owns properties. Assigning properties to first user...")
        
        first_user = users[0]
        print(f"Assigning properties to: {first_user.username}")
        
        # Get some existing properties
        unassigned_properties = Property.query.filter(Property.owner_id.is_(None)).limit(3).all()
        
        if unassigned_properties:
            for prop in unassigned_properties:
                prop.owner_id = first_user.id
                print(f"  Assigned: {prop.title}")
            
            db.session.commit()
            print("Properties assigned successfully!")
        else:
            print("No unassigned properties found.")
    
    # Create sample inquiries for first user
    if users:
        first_user = users[0]
        existing_inquiries = Inquiry.query.filter_by(user_id=first_user.id).count()
        
        if existing_inquiries == 0:
            print(f"\nCreating sample inquiries for {first_user.username}...")
            
            # Get some properties to inquire about
            properties = Property.query.limit(3).all()
            
            for prop in properties:
                inquiry = Inquiry(
                    user_id=first_user.id,
                    property_id=prop.id,
                    message=f"I'm very interested in this property. Could you provide more details about the neighborhood and nearby amenities?",
                    contact_phone=first_user.phone or "+254700123456",
                    preferred_contact="email",
                    status="pending"
                )
                db.session.add(inquiry)
                print(f"  Created inquiry for: {prop.title}")
            
            db.session.commit()
            print("Sample inquiries created successfully!")
    
    print("\nFinal user data summary:")
    for user in users:
        my_properties = Property.query.filter_by(owner_id=user.id).count()
        my_inquiries = Inquiry.query.filter_by(user_id=user.id).count()
        print(f"{user.username}: {my_properties} properties, {my_inquiries} inquiries")
