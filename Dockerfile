FROM python:3.10

COPY app/ /app
WORKDIR /app

RUN pip install -r requirements.txt
RUN flake8 .
