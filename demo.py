import os
import boto3
import random
from flask import Flask, request, abort
from prometheus_flask_exporter import PrometheusMetrics
# Add imports for OTel components into the application
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
# Import the AWS X-Ray for OTel Python IDs Generator into the application.
from opentelemetry.sdk.extension.aws.trace import AwsXRayIdGenerator
# Sends generated traces in the OTLP format to an ADOT Collector running on port 55678
otlp_exporter = OTLPSpanExporter(endpoint=os.getenv("OBSDEMO_OTLP_ENDPOINT"), insecure=True)
# Processes traces in batches as opposed to immediately one after the other
span_processor = BatchSpanProcessor(otlp_exporter)
# Configures the Global Tracer Provider
trace.set_tracer_provider(TracerProvider(active_span_processor=span_processor, id_generator=AwsXRayIdGenerator()))

from opentelemetry import propagate
from opentelemetry.sdk.extension.aws.trace.propagation.aws_xray_format import AwsXRayFormat
propagate.set_global_textmap(AwsXRayFormat())

from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
# Initialize instumentor for Botocore
BotocoreInstrumentor().instrument()


app = Flask(__name__)
metrics = PrometheusMetrics(app)
# Initialize instumentor for Flask web framework
FlaskInstrumentor().instrument_app(app)

# static information as metric
metrics.info('app_info', 'Application info', version='1.0.3')

tracer = trace.get_tracer(__name__)

@app.route('/')
def main():
    with tracer.start_as_current_span("index_request"):
        rc = random.randrange(0,4)
        return_codes = [404, 401, 500, 502, 301]
    if random.randrange(0, 100) > 85:
        abort(return_codes[rc])
    else:
        return "Working"

if __name__ == "__main__":
    app.run()

