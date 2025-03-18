# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port that Flask runs on
EXPOSE 5000

# Set the environment variable for Flask
ENV FLASK_APP=server.py

# Define the command to run the Flask app
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]