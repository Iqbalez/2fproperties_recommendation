# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port Streamlit runs on
EXPOSE 8501

# Define the command to run the Streamlit app
CMD echo "You can now view your Streamlit app in your browser at http://localhost:8501" && streamlit run app.py --server.port=8501 --server.address=0.0.0.0
