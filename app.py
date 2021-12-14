#/usr/bin/env python
""" Observability Demo App """
import logging
from logging.config import dictConfig
import os
import time
import sqlite3
import random


import requests

from flask import Flask, abort, session, g
from prometheus_flask_exporter import PrometheusMetrics
# Add imports for OTel components into the application

from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Setup a placeholder for the request start time
REQUEST_START_TIME = "requestStartTime"
# Sends generated traces in the OTLP format to an ADOT Collector running on port 55678
otlp_endpoint = os.getenv("OBSDEMO_OTLP_ENDPOINT") or "localhost:4317"
# Resource can be required for some backends, e.g. Jaeger
# If resource wouldn't be set - traces wouldn't appears in Jaeger
resource = Resource(attributes={
    "service.name": "observability-demo"
})

otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
trace.set_tracer_provider(TracerProvider(resource=resource))
span_processor = BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint=otlp_endpoint
            )
        )

trace.get_tracer_provider().add_span_processor(span_processor)


### CONFIGURE LOGGING ###
#LOGGING = {
#    'version': 1,
#    'disable_existing_loggers': True,
#    'formatters': {
#        'json': {'()': 'pythonjsonlogger.jsonlogger.JsonFormatter'},
#        'standard': {
#            'format': '%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] [traceID=%(otelTraceID)s spanID=%(otelSpanID)s resource.service.name=%(otelServiceName)s] - %(message)s', # pylint: disable=line-too-long
#            'datefmt': '%d-%m-%Y %H:%M:%S'
#        },
#    },
#    'handlers': {
#        'console': {
#            'level': 'DEBUG',
#            'class': 'logging.StreamHandler',
#            'formatter': 'json',
#        },
#        'syslog': {
#            'class': 'logging.handlers.SysLogHandler',
#            'address': ('localhost', 1514),
#            'facility': 'local0',
#            'formatter': 'standard'
#            },
#    },
#    'loggers': {
#        'root': {
#            'handlers': ['console'],
#            'level': 'DEBUG',
#            'propagate': True,
#        },
#    }
#}

LOG_FORMAT = '%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] [traceID=%(otelTraceID)s spanID=%(otelSpanID)s resource.service.name=%(otelServiceName)s] - %(message)s' # pylint: disable=line-too-long
LoggingInstrumentor().instrument(
        set_logging_format=True,
        log_level=logging.DEBUG,
        log_format=LOG_FORMAT
        )
#dictConfig(LOGGING)




app = Flask(__name__)
app.secret_key=os.getenv("OBSDEMO_APP_SECRET")
logger = logging.getLogger(__name__)
logger.info(f"OTLP Configured and pointing to {os.getenv('OBSDEMO_OTLP_ENDPOINT')}")


@app.before_request
def before_request_func():
    """ Set the session start time before each request """
    session[REQUEST_START_TIME] = int(time.time() * 1_000)

metrics = PrometheusMetrics(app)
# Initialize instumentor for Flask web framework
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
SQLite3Instrumentor().instrument()

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect("file::memory:?cache=shared")
        cur = db.cursor()
        cur.execute("CREATE TABLE obsdemo (timestamp integer, randomint integer)")
    return db

@app.teardown_appcontext
def close_connect(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# static information as metric
metrics.info('app_info', 'Application info', version='1.0.3')

tracer = trace.get_tracer(__name__)

@app.route('/')
def main():
    """ The primary route of the application for the index page """
    with tracer.start_as_current_span("index_request"):
        chosen_return_code = random.randrange(0,4)
        return_codes = [404, 401, 500, 502, 301]
        if random.randrange(0, 100) > 95:
            logger.info("Random error code selected")
            abort(return_codes[chosen_return_code])
        else:
            logger.info("Returning valid response")
            extreq = requests.get('http://127.0.0.1:5000/external_call')
            intreq = requests.get('http://127.0.0.1:5000/internal_call')
            text = "You should be seeing some spans now"

    return text

@app.route('/internal_call')
def internal_call():
    """ The primary route of the application for the index page """
    with tracer.start_as_current_span("index_request"):
        logger.info("Internal Code called")
        cur = get_db().cursor()
        cur.execute("SELECT * FROM obsdemo")
        cur.close()

    return "Successfully called internal code"

@app.route('/external_call')
def external_call():
    """ The primary route of the application for the index page """
    with tracer.start_as_current_span("index_request"):
        logger.info("External Code called")
        ext_site = requests.get("https://www.google.com/")
        cur = get_db().cursor()
        cur.execute(f"INSERT INTO obsdemo (timestamp, randomint)  VALUES ({time.time()}, {random.randrange(0, 1000)})")
        cur.close()

    return "Successfully called Google.com"

if __name__ == "__main__":
    app.run(host="0.0.0.0")
