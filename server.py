from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import pandas as pd
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)  # Allow credentials (cookies)
app.config['SECRET_KEY'] = 'your_fixed_strong_secret_key'  # Use a strong fixed secret key

# SQLite database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///real_estate.db'  # Database file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Feedback model
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    feedback = db.Column(db.String(50), nullable=False)

# Property model
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

# Initialize SQLite database
def init_db():
    with app.app_context():
        db.create_all()

# Ensure tables are created
init_db()

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    # Check if the username already exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({'error': 'Username already exists. Please choose a different username.'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, password=hashed_password)

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.session.remove()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and bcrypt.check_password_hash(user.password, password):
        session['user_id'] = user.id  # Store user id in session
        print(f"User logged in: {session['user_id']}")  # Debug statement
        return jsonify({'message': 'Login successful'}), 200
    return jsonify({'error': 'Invalid username or password'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)  # Remove user id from session
    return jsonify({'message': 'Logout successful'}), 200

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file.filename.endswith('.csv'):
        try:
            df = pd.read_csv(file)

            # Rename columns to match database schema
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

            # Check required columns
            required_columns = ['name', 'location', 'price', 'bedrooms', 'bathrooms', 'area', 'commute_time', 
                                'distance_train', 'distance_grocery', 'school_rating', 'property_images']
            if not all(col in df.columns for col in required_columns):
                return jsonify({'error': 'CSV is missing one or more required columns.'}), 400

            # Insert data into Property table
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

            return jsonify({'message': 'File uploaded successfully'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Invalid file format. Please upload a CSV file.'}), 400

@app.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    user_profile = request.json
    print("request.json: ", request.json)
    print("session : ", session)
    user_id = user_profile.get('user_id')  # Get the logged-in user's ID from the session
    
    user = User.query.filter_by(username=user_id).first()
    if user  :
        print("session :", session)
        session['user_id'] = user.id  # Store user id in session
        print(f"User logged in: {session['user_id']}")  # Debug statement
    
    # Check if the user is logged in
    if not user_id:
        return jsonify({'error': 'User not logged in.'}), 403

    # Debug statements
    print(f"User ID from session: {user_id}")  # Debug statement
    print(f"Session cookie received: {request.cookies}")  # Debug session cookie

    # Content-based filtering
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

    # Collaborative filtering (if user is logged in)
    collaborative_recommendations = []
    if user_id:
        user_feedback = Feedback.query.filter_by(user_id=user_id).all()
        liked_properties = [feedback.property_id for feedback in user_feedback if feedback.feedback == "like"]
        collaborative_recommendations = Property.query.filter(Property.id.in_(liked_properties)).all()

    # Combine recommendations
    hybrid_recommendations = list(set(content_based_recommendations + collaborative_recommendations))

    # Return the results
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
    } for prop in hybrid_recommendations])

@app.route('/api/feedback', methods=['POST'])
def feedback():
    feedback_data = request.json
    feedback = feedback_data.get('feedback')
    property_id = feedback_data.get('property_id')
    print(f"Property ID from session: {property_id}")  # Debug statement
    
    if not feedback or not property_id:
        return jsonify({'error': 'Missing feedback or property ID.'}), 400

    user_id =  feedback_data.get('user_id')  # Get user id from feedback_data
    print(f"User ID from session: {user_id}")  # Debug statement
    if not user_id:
        return jsonify({'error': 'User not logged in.'}), 403

    try:
        new_feedback = Feedback(user_id=user_id, property_id=property_id, feedback=feedback)
        db.session.add(new_feedback)
        db.session.commit()
        return jsonify({'message': 'Feedback recorded successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.session.remove()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=True)
