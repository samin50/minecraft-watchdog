# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir boto3 requests urllib3

ENV VERSION='1.3.1'

# Run watchdog.py when the container launches
ENTRYPOINT ["python", "-u", "./watchdog.py"]
