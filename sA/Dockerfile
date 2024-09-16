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

# Copy the rest of the application code into the container
COPY . /app/

# Expose the port that Django will run on
EXPOSE 8000

# Run the command to start the application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "myapp.wsgi:application"]