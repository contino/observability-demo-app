#/usr/bin/env python
""" Observability Demo App """
import os
import random
import time
from flask import Flask, abort, session
from prometheus_flask_exporter import PrometheusMetrics
# Add imports for OTel components into the application
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry import propagate
from opentelemetry.sdk.extension.aws.trace.propagation.aws_xray_format import AwsXRayFormat
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
# Import the AWS X-Ray for OTel Python IDs Generator into the application.
from opentelemetry.sdk.extension.aws.trace import AwsXRayIdGenerator
##### SET XRAY FORMAT ####
from opentelemetry.sdk.extension.aws.trace.propagation.aws_xray_format import (
    TRACE_ID_DELIMITER,
    TRACE_ID_FIRST_PART_LENGTH,
    TRACE_ID_VERSION,
)
# Sends generated traces in the OTLP format to an ADOT Collector running on port 55678
otlp_endpoint = os.getenv("OBSDEMO_OTLP_ENDPOINT") or "localhost:4317"
otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
# Processes traces in batches as opposed to immediately one after the other
span_processor = BatchSpanProcessor(otlp_exporter)
# Configures the Global Tracer Provider
trace.set_tracer_provider(
        TracerProvider(
            active_span_processor=span_processor,
            id_generator=AwsXRayIdGenerator()
            )
        )

propagate.set_global_textmap(AwsXRayFormat())

# Initialize instumentor for Botocore
BotocoreInstrumentor().instrument()



DIMENSION_API_NAME = "apiName"
DIMENSION_STATUS_CODE = "statusCode"
REQUEST_START_TIME = "requestStartTime"


def convert_otel_trace_id_to_xray(otel_trace_id_decimal):
    """ Convert the Open Telemetry Trace ID to an XRay Trace ID """
    otel_trace_id_hex = f"{otel_trace_id_decimal}"
    x_ray_trace_id = TRACE_ID_DELIMITER.join(
        [
            TRACE_ID_VERSION,
            otel_trace_id_hex[:TRACE_ID_FIRST_PART_LENGTH],
            otel_trace_id_hex[TRACE_ID_FIRST_PART_LENGTH:],
        ]
    )
    return f'{{"traceId": "{x_ray_trace_id}"}}'

app = Flask(__name__)
app.secret_key=os.getenv("OBSDEMO_APP_SECRET")


@app.before_request
def before_request_func():
    """ Set the session start time before each request """
    session[REQUEST_START_TIME] = int(time.time() * 1_000)

@app.after_request
def after_request_func(response):
    """ After each request, return the response

    TODO: Implement this function so that it calls something else with the same TraceID

    """
    # if request.path == "/outgoing-http-call":
    #     apiBytesSentCounter.add(
    #         response.calculate_content_length() + mimicPayloadSize(),
    #         {
    #             DIMENSION_API_NAME: request.path,
    #             DIMENSION_STATUS_CODE: response.status_code,
    #         },
    #     )

    #     apiLatencyRecorder.record(
    #         int(time.time() * 1_000) - session[REQUEST_START_TIME],
    #         {
    #             DIMENSION_API_NAME: request.path,
    #             DIMENSION_STATUS_CODE: response.status_code,
    #         },
    #     )

    return response

metrics = PrometheusMetrics(app)
# Initialize instumentor for Flask web framework
FlaskInstrumentor().instrument_app(app)

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
        abort(return_codes[chosen_return_code])
    else:
        return app.make_response(
                convert_otel_trace_id_to_xray(
                    trace.get_current_span().get_span_context().trace_id
                )
            )

if __name__ == "__main__":
    app.run(host="0.0.0.0")
