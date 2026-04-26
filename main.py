from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dbservice import create_app, db, bcrypt, User, Property, PropertyType, Location, Agent, Inquiry, UserRole, ListingType, PropertyStatus
from dbservice import LoginForm, RegistrationForm, PropertyForm, InquiryForm

# Initialize Flask app
app = create_app()
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Configuration for file uploads
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route('/')
def index():
    """Home page - display featured properties"""
    featured_properties = Property.query.filter_by(is_featured=True, status=PropertyStatus.AVAILABLE).limit(6).all()
    property_types = PropertyType.query.all()
    return render_template('index.html', properties=featured_properties, property_types=property_types)

@app.route('/index.html')
def index_html():
    """Home page - display featured properties (backward compatibility)"""
    return redirect(url_for('index'))

@app.route('/properties.html')
def properties_html():
    """Properties page (backward compatibility)"""
    return redirect(url_for('property_list'))

@app.route('/property-single.html')
def property_single_html():
    """Property single page (backward compatibility)"""
    return redirect(url_for('property_list'))

@app.route('/about.html')
def about_html():
    """About page (backward compatibility)"""
    return redirect(url_for('about'))

@app.route('/contact.html')
def contact_html():
    """Contact page (backward compatibility)"""
    return redirect(url_for('property_agents'))

@app.route('/services.html')
def services_html():
    """Services page (backward compatibility)"""
    return redirect(url_for('index'))

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.route('/property-list')
def property_list():
    """Property listing page with filters"""
    page = request.args.get('page', 1, type=int)
    listing_type = request.args.get('listing_type', '')
    property_type_id = request.args.get('property_type_id', type=int)
    location_id = request.args.get('location_id', type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    
    # Build query
    query = Property.query.filter_by(status=PropertyStatus.AVAILABLE)
    
    if listing_type:
        query = query.filter_by(listing_type=ListingType(listing_type))
    
    if property_type_id:
        query = query.filter_by(property_type_id=property_type_id)
    
    if location_id:
        query = query.filter_by(location_id=location_id)
    
    if min_price:
        query = query.filter(Property.price >= min_price)
    
    if max_price:
        query = query.filter(Property.price <= max_price)
    
    properties = query.order_by(Property.created_at.desc()).paginate(
        page=page, per_page=12, error_out=False
    )
    
    property_types = PropertyType.query.all()
    locations = Location.query.all()
    
    return render_template('properties.html', 
                         properties=properties, 
                         property_types=property_types,
                         locations=locations)

@app.route('/property-agent')
def property_agents():
    """Property agents page"""
    agents = Agent.query.filter_by(is_featured=True).all()
    return render_template('property-agent.html', agents=agents)

@app.route('/property/<int:property_id>')
def property_detail(property_id):
    """Property detail page"""
    property = Property.query.get_or_404(property_id)
    
    # Increment view count
    property.views_count += 1
    db.session.commit()
    
    # Get similar properties
    similar_properties = Property.query.filter(
        Property.property_type_id == property.property_type_id,
        Property.id != property.id,
        Property.status == PropertyStatus.AVAILABLE
    ).limit(3).all()
    
    return render_template('property-single.html', 
                         property=property, 
                         similar_properties=similar_properties)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=True)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user already exists
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html', form=form)
        
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken.', 'danger')
            return render_template('register.html', form=form)
        
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/add-property', methods=['GET', 'POST'])
@login_required
def add_property():
    """Add new property"""
    form = PropertyForm()
    
    # Populate choices
    form.property_type_id.choices = [(pt.id, pt.name) for pt in PropertyType.query.all()]
    form.location_id.choices = [(l.id, f"{l.city}, {l.state}") for l in Location.query.all()]
    
    if form.validate_on_submit():
        # Handle main image upload
        main_image = None
        if 'main_image' in request.files:
            file = request.files['main_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                main_image = filename
        
        # Create property
        property = Property(
            title=form.title.data,
            description=form.description.data,
            price=form.price.data,
            address=form.address.data,
            owner_id=current_user.id,
            property_type_id=form.property_type_id.data,
            location_id=form.location_id.data,
            listing_type=ListingType(form.listing_type.data),
            square_feet=form.square_feet.data,
            bedrooms=form.bedrooms.data,
            bathrooms=form.bathrooms.data,
            garages=form.garages.data,
            year_built=form.year_built.data,
            main_image=main_image
        )
        
        db.session.add(property)
        db.session.commit()
        
        flash('Property added successfully!', 'success')
        return redirect(url_for('property_detail', property_id=property.id))
    
    return render_template('add-property.html', form=form)

@app.route('/inquiry/<int:property_id>', methods=['POST'])
@login_required
def submit_inquiry(property_id):
    """Submit property inquiry"""
    property = Property.query.get_or_404(property_id)
    form = InquiryForm()
    
    if form.validate_on_submit():
        inquiry = Inquiry(
            property_id=property_id,
            user_id=current_user.id,
            message=form.message.data,
            contact_phone=form.contact_phone.data,
            preferred_contact=form.preferred_contact.data
        )
        
        db.session.add(inquiry)
        db.session.commit()
        
        flash('Your inquiry has been submitted successfully!', 'success')
        return redirect(url_for('property_detail', property_id=property_id))
    
    flash('Error submitting inquiry. Please try again.', 'danger')
    return redirect(url_for('property_detail', property_id=property_id))

# API Routes
@app.route('/api/properties')
def api_properties():
    """API endpoint to get properties"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    listing_type = request.args.get('listing_type', '')
    property_type_id = request.args.get('property_type_id', type=int)
    
    query = Property.query.filter_by(status=PropertyStatus.AVAILABLE)
    
    if listing_type:
        query = query.filter_by(listing_type=ListingType(listing_type))
    
    if property_type_id:
        query = query.filter_by(property_type_id=property_type_id)
    
    properties = query.paginate(page=page, per_page=per_page, error_out=False)
    
    result = {
        'properties': [
            {
                'id': prop.id,
                'title': prop.title,
                'description': prop.description[:200] + '...',
                'price': float(prop.price),
                'address': prop.address,
                'listing_type': prop.listing_type.value,
                'square_feet': prop.square_feet,
                'bedrooms': prop.bedrooms,
                'bathrooms': prop.bathrooms,
                'main_image': prop.main_image,
                'property_type': prop.property_type_obj.name if prop.property_type_obj else None,
                'location': f"{prop.location_obj.city}, {prop.location_obj.state}" if prop.location_obj else None,
                'created_at': prop.created_at.isoformat()
            }
            for prop in properties.items
        ],
        'pagination': {
            'page': properties.page,
            'pages': properties.pages,
            'per_page': properties.per_page,
            'total': properties.total,
            'has_next': properties.has_next,
            'has_prev': properties.has_prev
        }
    }
    
    return jsonify(result)

@app.route('/api/property-types')
def api_property_types():
    """API endpoint to get property types"""
    property_types = PropertyType.query.all()
    result = [
        {
            'id': pt.id,
            'name': pt.name,
            'description': pt.description,
            'icon_path': pt.icon_path,
            'properties_count': len(pt.properties)
        }
        for pt in property_types
    ]
    return jsonify(result)

@app.route('/api/locations')
def api_locations():
    """API endpoint to get locations"""
    locations = Location.query.all()
    result = [
        {
            'id': loc.id,
            'city': loc.city,
            'state': loc.state,
            'country': loc.country,
            'zip_code': loc.zip_code,
            'neighborhood': loc.neighborhood,
            'full_address': f"{loc.city}, {loc.state}, {loc.country}"
        }
        for loc in locations
    ]
    return jsonify(result)

@app.route('/api/search')
def api_search():
    """API endpoint for property search"""
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    
    search_query = Property.query.filter(
        Property.status == PropertyStatus.AVAILABLE
    ).filter(
        Property.title.contains(query) |
        Property.description.contains(query) |
        Property.address.contains(query)
    )
    
    properties = search_query.paginate(page=page, per_page=12, error_out=False)
    
    result = {
        'query': query,
        'properties': [
            {
                'id': prop.id,
                'title': prop.title,
                'price': float(prop.price),
                'address': prop.address,
                'listing_type': prop.listing_type.value,
                'main_image': prop.main_image,
                'property_type': prop.property_type_obj.name if prop.property_type_obj else None
            }
            for prop in properties.items
        ],
        'pagination': {
            'page': properties.page,
            'pages': properties.pages,
            'total': properties.total
        }
    }
    
    return jsonify(result)

def create_sample_data():
    """Create sample data for testing"""
    with app.app_context():
        if PropertyType.query.count() == 0:
            # Sample property types
            property_types = [
                PropertyType(name='Apartment', description='Modern apartments in urban areas', icon_path='img/icon-apartment.png'),
                PropertyType(name='Villa', description='Luxury villas with private spaces', icon_path='img/icon-villa.png'),
                PropertyType(name='Home', description='Family homes in residential areas', icon_path='img/icon-house.png'),
                PropertyType(name='Office', description='Commercial office spaces', icon_path='img/icon-office.png'),
                PropertyType(name='Building', description='Multi-story buildings', icon_path='img/icon-building.png'),
                PropertyType(name='Townhouse', description='Modern townhouses', icon_path='img/icon-townhouse.png'),
                PropertyType(name='Shop', description='Retail shop spaces', icon_path='img/icon-shop.png'),
                PropertyType(name='Garage', description='Parking garages', icon_path='img/icon-garage.png')
            ]
            
            # Sample locations
            locations = [
                Location(city='New York', state='NY', country='USA', zip_code='10001'),
                Location(city='Los Angeles', state='CA', country='USA', zip_code='90001'),
                Location(city='Chicago', state='IL', country='USA', zip_code='60601'),
                Location(city='Houston', state='TX', country='USA', zip_code='77001'),
                Location(city='Phoenix', state='AZ', country='USA', zip_code='85001'),
                Location(city='Philadelphia', state='PA', country='USA', zip_code='19101'),
                Location(city='San Antonio', state='TX', country='USA', zip_code='78201'),
                Location(city='San Diego', state='CA', country='USA', zip_code='92101')
            ]
            
            db.session.add_all(property_types)
            db.session.add_all(locations)
            db.session.commit()
            
            print("Sample data created successfully!")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_sample_data()
    app.run(debug=True, host='0.0.0.0', port=5000)