FROM python:3.10

COPY . /core
WORKDIR /core

RUN pip install -r requirements.txt
WORKDIR /core
RUN flake8 .
