# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container to /app
WORKDIR /app

# Install needed packages
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     curl \
#     software-properties-common \
#     git \
#     && rm -rf /var/lib/apt/lists/*

# Add a system user to run our application so it doesn't run as root
RUN useradd -m myuser
# Switch to the new user
# Copy the requirements file into the container at /app
COPY --chown=myuser:myuser requirements.txt /app
# Install any needed packages specified in requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt
# Copy the current directory contents into the container at /app
COPY --chown=myuser:myuser src/ /app
USER myuser
EXPOSE 8501
#HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
