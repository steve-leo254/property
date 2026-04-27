from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dbservice import create_app, db, bcrypt, User, Property, PropertyType, Location, Agent, Inquiry, UserRole, ListingType, PropertyStatus
from dbservice import LoginForm, RegistrationForm, PropertyForm, InquiryForm, AdminRegistrationForm

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

@app.route('/property-detail.html')
def property_single_html():
    """Property single page (backward compatibility)"""
    return redirect(url_for('property_list'))

@app.route('/property-detail')
def property_detail_alt():
    """Property detail page (backward compatibility)"""
    return redirect(url_for('property_list'))

@app.route('/propertydetails')
def property_details_alt():
    """Property detail page (backward compatibility)"""
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
    
    # Parse image gallery
    image_gallery = []
    if property.image_gallery:
        try:
            image_gallery = json.loads(property.image_gallery)
        except:
            image_gallery = []
    
    # Get similar properties
    similar_properties = Property.query.filter(
        Property.property_type_id == property.property_type_id,
        Property.id != property.id,
        Property.status == PropertyStatus.AVAILABLE
    ).limit(3).all()
    
    return render_template('property-detail.html', 
                         property=property, 
                         similar_properties=similar_properties,
                         image_gallery=image_gallery)

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
            
            # Redirect to appropriate dashboard based on user role
            if next_page:
                return redirect(next_page)
            elif user.role == UserRole.ADMIN:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
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

@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    """Admin registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = AdminRegistrationForm()
    if form.validate_on_submit():
        # Check if user already exists
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
            return render_template('admin/register.html', form=form)
        
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken.', 'danger')
            return render_template('admin/register.html', form=form)
        
        # Create new admin user
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            role=UserRole.ADMIN
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Admin account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('admin/register.html', form=form)

# Admin Routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard - only accessible by admin users"""
    if current_user.role != UserRole.ADMIN:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    # Get statistics
    total_properties = Property.query.count()
    total_users = User.query.count()
    total_agents = Agent.query.count()
    total_inquiries = Inquiry.query.count()
    
    # Get recent properties
    recent_properties = Property.query.order_by(Property.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_properties=total_properties,
                         total_users=total_users,
                         total_agents=total_agents,
                         total_inquiries=total_inquiries,
                         recent_properties=recent_properties)

@app.route('/admin/properties')
@login_required
def admin_properties():
    """Admin manage properties page"""
    if current_user.role != UserRole.ADMIN:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)
    properties = Property.query.order_by(Property.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/properties.html', properties=properties)

@app.route('/admin/users')
@login_required
def admin_users():
    """Admin manage users page"""
    if current_user.role != UserRole.ADMIN:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users.html', users=users)

@app.route('/admin/agents')
@login_required
def admin_agents():
    """Admin manage agents page"""
    if current_user.role != UserRole.ADMIN:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)
    agents = Agent.query.order_by(Agent.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/agents.html', agents=agents)

@app.route('/admin/inquiries')
@login_required
def admin_inquiries():
    """Admin manage inquiries page"""
    if current_user.role != UserRole.ADMIN:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)
    inquiries = Inquiry.query.order_by(Inquiry.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/inquiries.html', inquiries=inquiries)

@app.route('/admin/property/<int:property_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_property(property_id):
    """Admin edit property"""
    if current_user.role != UserRole.ADMIN:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    property = Property.query.get_or_404(property_id)
    form = PropertyForm(obj=property)
    
    # Populate choices
    form.property_type_id.choices = [(pt.id, pt.name) for pt in PropertyType.query.all()]
        
    if form.validate_on_submit():
        # Handle main image upload
        if 'main_image' in request.files:
            file = request.files['main_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                property.main_image = filename
        
        # Handle additional images upload
        if 'image_gallery' in request.files:
            files = request.files.getlist('image_gallery')
            new_gallery = []
            
            # Get existing gallery
            existing_gallery = []
            if property.image_gallery:
                try:
                    existing_gallery = json.loads(property.image_gallery)
                except:
                    existing_gallery = []
            
            # Add new images
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_')}_{filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    new_gallery.append(filename)
            
            # Combine existing and new images
            updated_gallery = existing_gallery + new_gallery
            property.image_gallery = json.dumps(updated_gallery) if updated_gallery else None
        
        # Update property
        property.title = form.title.data
        property.description = form.description.data
        property.price = form.price.data
        property.address = form.address.data
        property.property_type_id = form.property_type_id.data
        property.location_text = form.location.data
        property.listing_type = ListingType(form.listing_type.data)
        property.square_feet = form.square_feet.data
        property.bedrooms = form.bedrooms.data
        property.bathrooms = form.bathrooms.data
        property.garages = form.garages.data
        property.year_built = form.year_built.data
        
        db.session.commit()
        flash('Property updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    # Parse existing image gallery for display
    image_gallery = []
    if property.image_gallery:
        try:
            image_gallery = json.loads(property.image_gallery)
        except:
            image_gallery = []
    
    return render_template('admin/edit_property.html', form=form, property=property, image_gallery=image_gallery)

# User Routes
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    """User dashboard"""
    # Get user's properties with pagination (show 5 per page for dashboard)
    page = request.args.get('page', 1, type=int)
    my_properties = Property.query.filter_by(owner_id=current_user.id).order_by(Property.created_at.desc()).paginate(
        page=page, per_page=5, error_out=False
    )
    
    # Get user's inquiries
    my_inquiries = Inquiry.query.filter_by(user_id=current_user.id).order_by(Inquiry.created_at.desc()).all()
    
    # For now, saved properties will be empty (we can implement this later)
    saved_properties = []
    
    return render_template('user/dashboard.html',
                         my_properties=my_properties,
                         my_inquiries=my_inquiries,
                         saved_properties=saved_properties)

@app.route('/user/properties')
@login_required
def user_properties():
    """User's properties page"""
    page = request.args.get('page', 1, type=int)
    properties = Property.query.filter_by(owner_id=current_user.id).order_by(Property.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('user/properties.html', properties=properties)

@app.route('/user/inquiries')
@login_required
def user_inquiries():
    """User's inquiries page"""
    page = request.args.get('page', 1, type=int)
    inquiries = Inquiry.query.filter_by(user_id=current_user.id).order_by(Inquiry.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('user/inquiries.html', inquiries=inquiries)

@app.route('/user/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    """User profile page"""
    form = RegistrationForm(obj=current_user)
    form.submit.data = 'Update Profile'
    
    if form.validate_on_submit():
        # Check if email is being changed and if it's already taken
        if form.email.data != current_user.email:
            if User.query.filter_by(email=form.email.data).first():
                flash('Email already registered.', 'danger')
                return render_template('user/profile.html', form=form)
        
        # Check if username is being changed and if it's already taken
        if form.username.data != current_user.username:
            if User.query.filter_by(username=form.username.data).first():
                flash('Username already taken.', 'danger')
                return render_template('user/profile.html', form=form)
        
        # Update user info
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.phone = form.phone.data
        
        # Update password if provided
        if form.password.data:
            current_user.set_password(form.password.data)
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user_dashboard'))
    
    return render_template('user/profile.html', form=form)

@app.route('/user/property/<int:property_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_property(property_id):
    """User edit their own property"""
    property = Property.query.get_or_404(property_id)
    
    # Check if user owns this property
    if property.owner_id != current_user.id:
        flash('Access denied. You can only edit your own properties.', 'danger')
        return redirect(url_for('user_dashboard'))
    
    form = PropertyForm(obj=property)
    
    # Populate choices
    form.property_type_id.choices = [(pt.id, pt.name) for pt in PropertyType.query.all()]
        
    if form.validate_on_submit():
        # Handle main image upload
        if 'main_image' in request.files:
            file = request.files['main_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                property.main_image = filename
        
        # Update property
        property.title = form.title.data
        property.description = form.description.data
        property.price = form.price.data
        property.address = form.address.data
        property.property_type_id = form.property_type_id.data
        property.location_text = form.location.data
        property.listing_type = ListingType(form.listing_type.data)
        property.square_feet = form.square_feet.data
        property.bedrooms = form.bedrooms.data
        property.bathrooms = form.bathrooms.data
        property.garages = form.garages.data
        property.year_built = form.year_built.data
        
        db.session.commit()
        return redirect(url_for('user_properties'))
    
    return render_template('user/edit_property.html', form=form, property=property)

@app.route('/add-property', methods=['GET', 'POST'])
@login_required
def add_property():
    """Add new property - only for agents and admins"""
    if current_user.role not in [UserRole.AGENT, UserRole.ADMIN]:
        flash('Only agents and admins can add properties.', 'danger')
        return redirect(url_for('property_list'))
    
    form = PropertyForm()
    
    # Populate choices
    form.property_type_id.choices = [(pt.id, pt.name) for pt in PropertyType.query.all()]
        
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
        
        # Handle additional images upload
        image_gallery = []
        if 'image_gallery' in request.files:
            files = request.files.getlist('image_gallery')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_')}_{filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_gallery.append(filename)
        
        # Create property
        property = Property(
            title=form.title.data,
            description=form.description.data,
            price=form.price.data,
            address=form.address.data,
            owner_id=current_user.id,
            property_type_id=form.property_type_id.data,
            location_text=form.location.data,
            listing_type=ListingType(form.listing_type.data),
            square_feet=form.square_feet.data,
            bedrooms=form.bedrooms.data,
            bathrooms=form.bathrooms.data,
            garages=form.garages.data,
            year_built=form.year_built.data,
            main_image=main_image,
            image_gallery=json.dumps(image_gallery) if image_gallery else None
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

@app.route('/admin/setup', methods=['GET', 'POST'])
def admin_setup():
    """One-time admin setup page"""
    # Check if admin already exists
    existing_admin = User.query.filter_by(role=UserRole.ADMIN).first()
    if existing_admin:
        flash('Administrator account already exists. Please use login.', 'warning')
        return redirect(url_for('login'))
    
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = AdminRegistrationForm()
    
    if form.validate_on_submit():
        # Create admin user
        admin_user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            role=UserRole(form.role.data)
        )
        admin_user.set_password(form.password.data)
        
        db.session.add(admin_user)
        db.session.commit()
        
        flash('Administrator account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('admin/setup.html', form=form)

# Admin Inquiry Management Routes
@app.route('/admin/inquiries/<int:inquiry_id>/reply', methods=['POST'])
@login_required
def admin_reply_inquiry(inquiry_id):
    """Handle reply to inquiry"""
    if current_user.role != UserRole.ADMIN:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    inquiry = Inquiry.query.get_or_404(inquiry_id)
    
    try:
        data = request.get_json()
        reply_message = data.get('message', '')
        
        if not reply_message.strip():
            return jsonify({'success': False, 'message': 'Message cannot be empty'}), 400
        
        # Here you would normally send an email
        # For now, we'll just mark as responded and save the reply
        inquiry.status = 'responded'
        inquiry.admin_reply = reply_message
        inquiry.responded_at = datetime.utcnow()
        inquiry.responded_by = current_user.id
        
        db.session.commit()
        
        # TODO: Add actual email sending functionality
        # send_email(
        #     to=inquiry.user.email,
        #     subject='Re: Your Property Inquiry',
        #     body=reply_message
        # )
        
        return jsonify({'success': True, 'message': 'Reply sent successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/inquiries/<int:inquiry_id>/mark-responded', methods=['POST'])
@login_required
def admin_mark_inquiry_responded(inquiry_id):
    """Mark inquiry as responded"""
    if current_user.role != UserRole.ADMIN:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    inquiry = Inquiry.query.get_or_404(inquiry_id)
    
    try:
        inquiry.status = 'responded'
        inquiry.responded_at = datetime.utcnow()
        inquiry.responded_by = current_user.id
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Inquiry marked as responded'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_sample_data()
    app.run(debug=True, host='0.0.0.0', port=5000)