from flask import Flask
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, IntegerField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange
from enum import Enum
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myproperty.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)

def create_app():
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='.', 
                static_url_path='')
    app.config['SECRET_KEY'] = 'your_secret_key_here'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myproperty.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    return app

# Enums
class UserRole(Enum):
    USER = 'USER'
    ADMIN = 'ADMIN'
    AGENT = 'AGENT'

class ListingType(Enum):
    FOR_SALE = 'FOR_SALE'
    FOR_RENT = 'FOR_RENT'

class PropertyStatus(Enum):
    AVAILABLE = 'AVAILABLE'
    SOLD = 'SOLD'
    RENTED = 'RENTED'
    PENDING = 'PENDING'

# Database Models
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.Enum(UserRole), default=UserRole.USER)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    properties = db.relationship('Property', backref='owner', lazy=True)
    inquiries = db.relationship('Inquiry', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class PropertyType(db.Model):
    __tablename__ = 'property_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    icon_path = db.Column(db.String(100))  # Path to icon image
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    properties = db.relationship('Property', backref='property_type_obj', lazy=True)

class Location(db.Model):
    __tablename__ = 'locations'
    
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100))
    country = db.Column(db.String(100), default='USA')
    zip_code = db.Column(db.String(20))
    neighborhood = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    properties = db.relationship('Property', backref='location_obj', lazy=True)

class Agent(db.Model):
    __tablename__ = 'agents'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    license_number = db.Column(db.String(50), unique=True)
    designation = db.Column(db.String(100))
    bio = db.Column(db.Text)
    experience_years = db.Column(db.Integer)
    profile_image = db.Column(db.String(200))
    facebook_url = db.Column(db.String(200))
    twitter_url = db.Column(db.String(200))
    instagram_url = db.Column(db.String(200))
    linkedin_url = db.Column(db.String(200))
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    properties = db.relationship('Property', backref='agent', lazy=True)

class Property(db.Model):
    __tablename__ = 'properties'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    address = db.Column(db.String(500), nullable=False)
    
    # Foreign Keys
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'))
    property_type_id = db.Column(db.Integer, db.ForeignKey('property_types.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    
    # Property Details
    listing_type = db.Column(db.Enum(ListingType), nullable=False)
    status = db.Column(db.Enum(PropertyStatus), default=PropertyStatus.AVAILABLE)
    year_built = db.Column(db.Integer)
    
    # Specifications
    square_feet = db.Column(db.Integer)
    bedrooms = db.Column(db.Integer)
    bathrooms = db.Column(db.Integer)
    garages = db.Column(db.Integer)
    lot_size = db.Column(db.Numeric(10, 2))
    
    # Features
    features = db.Column(db.Text)  # JSON string of features
    amenities = db.Column(db.Text)  # JSON string of amenities
    
    # Media
    main_image = db.Column(db.String(200))
    image_gallery = db.Column(db.Text)  # JSON string of image paths
    virtual_tour_url = db.Column(db.String(500))
    
    # Metadata
    views_count = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    inquiries = db.relationship('Inquiry', backref='property', lazy=True, cascade='all, delete-orphan')

class Inquiry(db.Model):
    __tablename__ = 'inquiries'
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    contact_phone = db.Column(db.String(20))
    preferred_contact = db.Column(db.String(20), default='email')
    status = db.Column(db.String(20), default='pending')  # pending, responded, closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# WTForms Classes
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    phone = StringField('Phone')
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', 
                                   validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class PropertyForm(FlaskForm):
    title = StringField('Property Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0)])
    address = StringField('Address', validators=[DataRequired()])
    property_type_id = SelectField('Property Type', coerce=int, validators=[DataRequired()])
    location_id = SelectField('Location', coerce=int, validators=[DataRequired()])
    listing_type = SelectField('Listing Type', 
                             choices=[('FOR_SALE', 'For Sale'), ('FOR_RENT', 'For Rent')],
                             validators=[DataRequired()])
    square_feet = IntegerField('Square Feet', validators=[NumberRange(min=0)])
    bedrooms = IntegerField('Bedrooms', validators=[NumberRange(min=0)])
    bathrooms = IntegerField('Bathrooms', validators=[NumberRange(min=0)])
    garages = IntegerField('Garages', validators=[NumberRange(min=0)])
    year_built = IntegerField('Year Built', validators=[NumberRange(min=1800, max=datetime.utcnow().year)])
    submit = SubmitField('Save Property')

class InquiryForm(FlaskForm):
    message = TextAreaField('Message', validators=[DataRequired()])
    contact_phone = StringField('Phone Number')
    preferred_contact = SelectField('Preferred Contact Method',
                                  choices=[('email', 'Email'), ('phone', 'Phone')],
                                  default='email')
    submit = SubmitField('Send Inquiry')
