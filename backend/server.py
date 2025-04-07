# app.py - Full Code with NLP Integrations
from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import pandas as pd
import numpy as np
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
from nltk.sentiment import SentimentIntensityAnalyzer
import tensorflow as tf

# Initialize NLP models
nlp_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
sia = SentimentIntensityAnalyzer()

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.config['SECRET_KEY'] = 'your_strong_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///real_estate.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Database Models with NLP Fields
class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)  # NLP: Property description analysis
    embedding = db.Column(db.LargeBinary)  # NLP: Stored embeddings
    # ... [other fields same as before]

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # ... [existing fields]
    feedback_text = db.Column(db.Text)  # NLP: Sentiment analysis
    sentiment_score = db.Column(db.Float)  # NLP: Weighted feedback

# Neural Collaborative Filtering Model
def create_ncf_model(num_users, num_properties):
    user_input = tf.keras.Input(shape=(1,))
    property_input = tf.keras.Input(shape=(1,))
    
    user_embed = tf.keras.layers.Embedding(num_users, 64)(user_input)
    property_embed = tf.keras.layers.Embedding(num_properties, 64)(property_input)
    
    merged = tf.keras.layers.Concatenate()([user_embed, property_embed])
    dense = tf.keras.layers.Dense(128, activation='relu')(merged)
    output = tf.keras.layers.Dense(1, activation='sigmoid')(dense)
    
    return tf.keras.Model(inputs=[user_input, property_input], outputs=output)

# NLP Search Endpoint
@app.route('/api/nlp-search', methods=['POST'])
def nlp_search():
    query = request.json.get('query', '')
    query_embedding = nlp_model.encode(query).tobytes()
    
    properties = Property.query.all()
    results = []
    
    for prop in properties:
        if not prop.embedding:
            continue
        prop_embedding = np.frombuffer(prop.embedding)
        similarity = np.dot(nlp_model.encode(query), prop_embedding)
        
        if similarity > 0.65:
            results.append({
                'id': prop.id,
                'name': prop.name,
                'similarity': float(similarity),
                'price': prop.price,
                'location': prop.location
            })
    
    return jsonify(sorted(results, key=lambda x: x['similarity'], reverse=True))

# Enhanced Feedback Endpoint with Sentiment Analysis
@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    feedback_text = data.get('feedback_text', '')
    
    # Sentiment Analysis
    sentiment = sia.polarity_scores(feedback_text)
    weighted_score = sentiment['compound']  # Range: -1 to 1
    
    new_feedback = Feedback(
        user_id=session.get('user_id'),
        property_id=data['property_id'],
        feedback=data['feedback'],
        feedback_text=feedback_text,
        sentiment_score=weighted_score
    )
    
    db.session.add(new_feedback)
    db.session.commit()
    
    return jsonify({
        'message': 'Feedback saved',
        'sentiment_score': weighted_score
    }), 200

# Modified Upload Endpoint with NLP Processing
@app.route('/api/upload', methods=['POST'])
def upload_file():
    # ... [existing code]
    for _, row in df.iterrows():
        description = f"{row['name']} in {row['location']}. {row.get('description', '')}"
        embedding = nlp_model.encode(description).tobytes()
        
        property = Property(
            description=description,
            embedding=embedding,
            # ... [other fields]
        )
        db.session.add(property)
    # ... [remaining code]

# Frontend (Streamlit) NLP Integration
def nlp_search_interface():
    st.header("🔍 Natural Language Search")
    query = st.text_input("Describe your ideal property:")
    
    if query:
        response = requests.post(
            "http://localhost:5000/api/nlp-search",
            json={"query": query}
        )
        results = response.json()
        
        for prop in results:
            st.write(f"""
            **{prop['name']}**  
            *Similarity: {prop['similarity']:.2f}*  
            Price: ${prop['price']:,.0f}  
            Location: {prop['location']}
            """)

# Training the Neural Model
def train_ncf_model():
    users = User.query.all()
    properties = Property.query.all()
    feedbacks = Feedback.query.all()
    
    model = create_ncf_model(len(users), len(properties))
    model.compile(optimizer='adam', loss='binary_crossentropy')
    
    # Prepare training data
    user_ids = [f.user_id for f in feedbacks]
    property_ids = [f.property_id for f in feedbacks]
    labels = [1 if f.feedback == 'like' else 0 for f in feedbacks]
    
    model.fit(
        x=[np.array(user_ids), np.array(property_ids)],
        y=np.array(labels),
        epochs=10,
        batch_size=32
    )
    
    return model

if __name__ == '__main__':
    # Initialize NLP components
    with app.app_context():
        # Create/update database tables
        db.create_all()
        
        # Initial training
        train_ncf_model()
    
    app.run(debug=True)
