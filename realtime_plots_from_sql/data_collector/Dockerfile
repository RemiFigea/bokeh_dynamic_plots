FROM python:3.10.12-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    python -m pip install --upgrade pip

COPY requirements.txt /

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/

WORKDIR /app

CMD ["python", "scripts/collect_data.py"]
