from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import pandas as pd
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.config['SECRET_KEY'] = 'your_fixed_strong_secret_key'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///real_estate.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    feedback = db.Column(db.String(50), nullable=False)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    bedrooms = db.Column(db.Integer, nullable=False)
    bathrooms = db.Column(db.Integer, nullable=False)
    area = db.Column(db.Float, nullable=False)
    commute_time = db.Column(db.Integer, nullable=False)
    school_rating = db.Column(db.Integer, nullable=False)
    distance_train = db.Column(db.Float, nullable=False)
    distance_grocery = db.Column(db.Float, nullable=False)
    property_images = db.Column(db.String(250), nullable=True)

def init_db():
    with app.app_context():
        db.create_all()

def load_csv_directly(filepath):
    with app.app_context():
        try:
            df = pd.read_csv(filepath)
            df.rename(columns={
                'Property Name': 'name',
                'Location': 'location',
                'Price (SGD)': 'price',
                'No. of Bedrooms': 'bedrooms',
                'No. of Bathrooms': 'bathrooms',
                'House Area (SQM)': 'area',
                'Commute Time (mins)': 'commute_time',
                'School Rating': 'school_rating',
                'Distance to Train Station (km)': 'distance_train',
                'Distance to Grocery Store (km)': 'distance_grocery',
                'Property Images': 'property_images'
            }, inplace=True)

            required_columns = ['name', 'location', 'price', 'bedrooms', 'bathrooms', 
                              'area', 'commute_time', 'distance_train', 'distance_grocery',
                              'school_rating', 'property_images']

            if not all(col in df.columns for col in required_columns):
                raise ValueError('CSV missing required columns')

            # Clear existing data
            db.session.query(Property).delete()
            
            for _, row in df.iterrows():
                property = Property(
                    name=row['name'],
                    location=row['location'],
                    price=row['price'],
                    bedrooms=row['bedrooms'],
                    bathrooms=row['bathrooms'],
                    area=row['area'],
                    commute_time=row['commute_time'],
                    school_rating=row['school_rating'],
                    distance_train=row['distance_train'],
                    distance_grocery=row['distance_grocery'],
                    property_images=row['property_images']
                )
                db.session.add(property)
            db.session.commit()
            print("CSV data loaded successfully")
        except Exception as e:
            db.session.rollback()
            print(f"Error loading CSV: {str(e)}")
            raise

# Initialize database and load CSV
init_db()
load_csv_directly('sg_condo_data.csv')

# Authentication endpoints
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
        
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username exists'}), 400
        
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, password=hashed_password)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User registered'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()
    
    if user and bcrypt.check_password_hash(user.password, data.get('password')):
        session['user_id'] = user.id
        return jsonify({'message': 'Login successful'}), 200
        
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out'}), 200

# Recommendation endpoint
@app.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    user_profile = request.json
    
    # Fix: Use user_id directly from request instead of from session
    user_id = user_profile.get('user_id')
    
    # Find the user by username
    user = User.query.filter_by(username=user_id).first()
    
    # If user exists, authorize the request
    if user:
        # Set user ID in session for future requests
        session['user_id'] = user.id
        
        # Proceed with the recommendation logic
        content_based_recommendations = Property.query.filter(
            Property.price <= user_profile['budget'],
            Property.bedrooms >= user_profile['min_bedrooms'],
            Property.bathrooms >= user_profile['min_bathrooms'],
            Property.area >= user_profile['min_sqft'],
            Property.commute_time <= user_profile['max_commute'],
            Property.distance_train <= user_profile['max_distance_train_station'],
            Property.distance_grocery <= user_profile['max_distance_grocery'],
            Property.school_rating >= user_profile['min_school_rating']
        ).all()
        
        # Return the results as before
        return jsonify([{
            'id': prop.id,
            'name': prop.name,
            'location': prop.location,
            'price': prop.price,
            'bedrooms': prop.bedrooms,
            'bathrooms': prop.bathrooms,
            'area': prop.area,
            'commute_time': prop.commute_time,
            'school_rating': prop.school_rating,
            'distance_train': prop.distance_train,
            'distance_grocery': prop.distance_grocery,
            'property_images': prop.property_images
        } for prop in content_based_recommendations])
    else:
        return jsonify({'error': 'Unauthorized'}), 401


# Feedback endpoint 
@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    # Feedback handling logic
    # ...

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
