# observability-demo-app

A basic Python Flask application that randomly returns an HTTP error for 25% of queries.

By default, this works in AWS only and is configured to use X-Ray and Prometheus.

Prometheus should scrape the `/metrics` endpoint of this application

## Getting up and running

1. Create a virtualenv
2. Activate the virtualenv
3. Install the requirements: `pip install -r requirements.txt`
4. Set the `OBSDEMO_OTLP_ENDPOINT` environment variable to point to your OTLP collector
5. Run the app `python demo.py`

The app is now available at [http://localhost:5000/](http://localhost:5000/)
