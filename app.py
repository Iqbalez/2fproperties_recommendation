import streamlit as st
import requests
import re

# Initialize session state to track feedback, recommendations, and user login
if "submitted_feedback" not in st.session_state:
    st.session_state.submitted_feedback = {}

if "recommendations" not in st.session_state:
    st.session_state.recommendations = []

if "user_id" not in st.session_state:
    st.session_state.user_id = None

# Define the backend API URL
# APP_URL = "https://real-estate-recommender-3vbi.onrender.com"
APP_URL = "http://127.0.0.1:10000"



# Title of the application
st.title("🏡 Real Estate Recommender System")

# Password validation function
def validate_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search("[a-z]", password):
        return "Password must contain at least one lowercase letter."
    if not re.search("[A-Z]", password):
        return "Password must contain at least one uppercase letter."
    if not re.search("[0-9]", password):
        return "Password must contain at least one digit."
    if not re.search("[!@#$%^&*()_+=-]", password):
        return "Password must contain at least one special character."
    return None

# Create a requests.Session object for cookie persistence
session = requests.Session()

# User authentication functions
def register(username, password):
    response = session.post(f'{APP_URL}/api/register', json={'username': username, 'password': password})
    return response

def login(username, password):
    response = session.post(f'{APP_URL}/api/login', json={'username': username, 'password': password})
    if response.status_code == 200:
        st.session_state.user_id = username  # Store username in session state
    return response

def logout():
    response = session.post(f'{APP_URL}/api/logout')
    if response.status_code == 200:
        st.session_state.user_id = None
        st.session_state.recommendations = []  # Clear recommendations on logout
        st.session_state.submitted_feedback = {}  # Clear feedback on logout
    return response

# User registration and login forms
if st.session_state.user_id is None:
    st.subheader("👤 User Authentication")
    with st.form(key='auth_form'):
        auth_option = st.radio("Choose an option:", ["Register", "Login"])
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type='password', placeholder="Enter your password")
        submit_button = st.form_submit_button(label='Submit')

        if submit_button:
            if auth_option == "Register":
                password_error = validate_password(password)
                if password_error:
                    st.error(f"❌ {password_error}")
                else:
                    response = register(username, password)
                    if response.status_code == 201:
                        st.success("✅ Registration successful! You can now log in.")
                    else:
                        try:
                            error_message = response.json().get('error', 'An unknown error occurred.')
                        except ValueError:
                            error_message = response.text
                        st.error(f"❌ {error_message}")
            else:  # Login
                response = login(username, password)
                if response.status_code == 200:
                    st.success("✅ Login successful!")
                else:
                    try:
                        error_message = response.json().get('error', 'Invalid username or password.')
                    except ValueError:
                        error_message = response.text
                    st.error(f"❌ {error_message}")

# Logout button for logged-in users
if st.session_state.user_id is not None:
    st.subheader(f"Welcome, {st.session_state.user_id}!")
    if st.button("Logout"):
        logout()
        st.success("✅ Logout successful!")

# Inform users that file upload is disabled and data is preloaded
if st.session_state.user_id is not None:
    st.info("📂 File upload disabled. Property data is preloaded on the server.")

    # User input form for recommendations
    with st.form(key='user_profile_form'):
        st.subheader("🔍 Property Recommendations")
        col1, col2 = st.columns(2)
        with col1:
            budget = st.number_input("💰 Budget (SGD)", min_value=100000, step=10000, value=2000000)
            property_type = st.selectbox("🏠 Property Type", options=["Apartment", "Condominium"])
            min_bedrooms = st.number_input("🛏️ Minimum Bedrooms", min_value=1, step=1, value=2)
            min_bathrooms = st.number_input("🛁 Minimum Bathrooms", min_value=1, step=1, value=1)
        with col2:
            min_sqft = st.number_input("📏 Minimum Square Footage (SQM)", min_value=10, step=10, value=50)
            max_commute = st.number_input("🚗 Maximum Commute Time (mins)", min_value=0, step=5, value=30)
            max_distance_train_station = st.number_input("🚆 Max Distance to Train Station (km)", min_value=0.0, step=0.1, value=1.0)
            max_distance_grocery = st.number_input("🛒 Max Distance to Grocery Store (km)", min_value=0.0, step=0.1, value=1.0)
            min_school_rating = st.number_input("🏫 Minimum School Rating", min_value=1, max_value=10, value=7)

        submit_button = st.form_submit_button(label='Get Recommendations')

    if submit_button:
        user_profile = {
            'user_id': st.session_state.user_id,  # Include user_id for backend authentication
            'budget': budget,
            'property_type': property_type,
            'min_bedrooms': min_bedrooms,
            'min_bathrooms': min_bathrooms,
            'min_sqft': min_sqft,
            'max_commute': max_commute,
            'max_distance_train_station': max_distance_train_station,
            'max_distance_grocery': max_distance_grocery,
            'min_school_rating': min_school_rating,
        }
        response = session.post(f'{APP_URL}/api/recommendations', json=user_profile)
        if response.status_code == 200:
            st.session_state.recommendations = response.json()
        else:
            try:
                error_message = response.json().get('error', 'An unknown error occurred.')
            except ValueError:
                error_message = response.text
            st.error(f"❌ Error: {error_message}")

    # Display recommendations if available
    if st.session_state.recommendations:
        st.subheader("🏠 Recommended Properties")
        for house in st.session_state.recommendations:
            property_id = house.get('id')
            col1, col2 = st.columns([1, 2])
            with col1:
                image_url = house.get("property_images")
                if image_url:
                    st.image(image_url, caption=house.get("name", "Property"), use_container_width=True)
                else:
                    st.warning("No image available for this property.")
            with col2:
                st.markdown(f"""
                **🏡 Property Name:** {house.get('name', 'N/A')}
                **📍 Location:** {house.get('location', 'N/A')}
                **💲 Price:** SGD {house.get('price', 'N/A'):,.0f}
                **📏 Size:** {house.get('area', 'N/A')} SQM
                **🛏️ Bedrooms:** {house.get('bedrooms', 'N/A')}
                **🛁 Bathrooms:** {house.get('bathrooms', 'N/A')}
                """)

            # Feedback radio buttons
            feedback = st.radio(
                f"Do you like this property? ({house.get('name')})",
                ["No Feedback", "👍 Like", "👎 Dislike"],
                key=f"feedback_{property_id}"
            )

            if feedback != "No Feedback":
                if st.session_state.user_id is not None:
                    feedback_response = session.post(
                        f'{APP_URL}/api/feedback',
                        json={
                            'feedback': feedback,
                            'property_id': property_id,
                            'user_id': st.session_state.user_id
                        }
                    )
                    if feedback_response.status_code == 200:
                        st.success("✅ Feedback submitted!")
                        st.session_state.submitted_feedback[property_id] = feedback
                    else:
                        try:
                            error_message = feedback_response.json().get('error', 'Failed to submit feedback.')
                        except ValueError:
                            error_message = feedback_response.text
                        st.error(f"❌ {error_message}")
                else:
                    st.error("🔒 Please log in to submit feedback.")
            else:
                if property_id in st.session_state.submitted_feedback:
                    st.info(f"✅ You have already submitted feedback for this property: **{st.session_state.submitted_feedback[property_id]}**")
                else:
                    st.info("ℹ️ No feedback yet for this property.")

    elif submit_button and not st.session_state.recommendations:
        st.warning("⚠️ No properties match your criteria.")

else:
    st.info("🔒 Please log in or register to get property recommendations.")
