FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ref

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-u" ,"run.py"]
