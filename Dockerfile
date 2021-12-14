# syntax=docker/dockerfile:1
FROM python:3.8-slim-buster
ENV PYTHONUNBUFFERED=1
ENV OBSDEMO_OTLP_ENDPOINT="NONE"
ENV OBSDEMO_APP_SECRET="NONE"
RUN apt update && apt upgrade -y
WORKDIR /opt/app
COPY requirements.txt /opt/app/
RUN pip install -r /opt/app/requirements.txt
COPY . /opt/app

EXPOSE 5000

ENTRYPOINT ["python", "/opt/app/app.py"]
