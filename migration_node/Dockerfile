FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# Copy your project files into the container
COPY . /app/

# Make the entrypoint script executable
RUN chmod +x entrypoint.sh

# Run the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]