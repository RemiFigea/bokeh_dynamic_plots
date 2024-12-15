FROM python:3.10.12-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    python -m pip install --upgrade pip

COPY requirements.txt /

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/

WORKDIR /app

EXPOSE 5006

# To allow Bokeh server on a specific endpoint (e.g., a remote server IP)
# Uncomment the following line and replace with the desired origin IP and port
#CMD ["bokeh", "serve", "scripts/plot_realtime.py", "--allow-websocket-origin", "<IP_of_your_instance>:5006"]

# Default command to start Bokeh server without restricting origin
CMD ["bokeh", "serve", "scripts/plot_realtime.py"]
