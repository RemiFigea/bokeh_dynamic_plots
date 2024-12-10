FROM python:3.10.12-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    python -m pip install --upgrade pip

COPY requirements.txt /

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/

WORKDIR /app

EXPOSE 7860

CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "4", "flask_app:app"]

