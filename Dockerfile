# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container to /app
WORKDIR /app

# Add a system user to run our application so it doesn't run as root
RUN useradd -m myuser
# Copy the requirements file into the container at /app
COPY --chown=myuser:myuser requirements.txt /app

# Install any needed packages specified in requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt
# update the title in the template so it is always correct, e.g. during link expansion/sharing
RUN sed -i 's/<title>Streamlit<\/title>/<title>Emily Tarot - Virtual Tarot Readings<\/title>/g' /usr/local/lib/python3.10/site-packages/streamlit/static/index.html

# Copy the current directory contents into the container at /app
COPY --chown=myuser:myuser src/ /app
RUN mkdir /app/tarotSessions
RUN chown myuser:myuser /app/tarotSessions

# Switch to the new user
USER myuser
EXPOSE 8501
#HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
