# Use an official Python runtime as a parent image
FROM python:3.12

# Set environment variables to avoid buffering
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy your project files into the container
COPY . /app/

# No need for CMD here, the entrypoint script will handle starting the application