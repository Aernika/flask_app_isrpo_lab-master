from flask import Flask, jsonify, request, abort, make_response
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
import uuid
import random
import time
import logging
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

app = Flask(__name__)
CORS(app)

# Swagger setup
swagger_url = "/swaggerui"
swaggerui_blueprint = get_swaggerui_blueprint(
    swagger_url,
    f"{swagger_url}/swagger.json",
    config={"app_name": "MUSICAL CATALOG API"}
)
app.register_blueprint(swaggerui_blueprint, url_prefix=swagger_url)

# Prometheus Metrics
SONGS_API_REQUESTS = Counter('songs_api_requests_total', 'Total API requests for Songs', ['method', 'endpoint'])

# Logging into file
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# OpenTelemetry configuration
resource = Resource(attributes={"service.name": "flask-musical-service"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)
otlp_exporter = OTLPSpanExporter(endpoint="tempo:4317", insecure=True)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

# Instrument Flask app with OpenTelemetry
FlaskInstrumentor().instrument_app(app)


@app.route(f'{swagger_url}/swagger.json')
def swagger_json():
    with open('oas.yaml', 'r') as file:
        swagger_json = file.read()
    response = make_response(swagger_json)
    response.headers['Content-Type'] = 'application/yaml'
    return response

# In-memory song storage
songs = {}


@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# Example trace spans with delay and errors
@app.route('/songs', methods=['GET'])
def get_songs():
    with tracer.start_as_current_span("get_songs") as span:
        delay = random.uniform(0.1, 0.5)
        time.sleep(delay)  # Random delay for testing
        span.set_attribute("delay", delay)
        if random.choice([True, False]):
            span.set_status(trace.status.Status(trace.status.StatusCode.ERROR, "Randomly triggered error"))
            abort(500, description="Randomly triggered error for tracing")
        logger.info("GET /songs request received")
        SONGS_API_REQUESTS.labels(method='GET', endpoint='/songs').inc()
        return jsonify(list(songs.values())), 200


@app.route('/songs', methods=['POST'])
def add_song():
    with tracer.start_as_current_span("add_song") as span:
        data = request.get_json()
        song_id = str(uuid.uuid4())
        song = {
            'id': song_id,
            'title': data.get('title'),
            'author': data.get('author'),
            'genre': data.get('genre'),
            'year': data.get('year')
        }
        logger.info("POST /songs request received")
        SONGS_API_REQUESTS.labels(method='POST', endpoint='/songs').inc()
        songs[song_id] = song
        return jsonify(song), 201


@app.route('/songs/<song_id>', methods=['GET'])
def get_song(song_id):
    with tracer.start_as_current_span("get_song_by_id") as span:
        logger.info(f"GET /songs/{song_id} request received")
        span.set_attribute("song_id", song_id)
        SONGS_API_REQUESTS.labels(method='GET', endpoint='/songs/<song_id>').inc()
        song = songs.get(song_id)
        if not song:
            span.set_status(trace.status.Status(trace.status.StatusCode.ERROR, "Song not found"))
            abort(404, description="Song not found")
        return jsonify(song), 200


@app.route('/songs/<song_id>', methods=['PUT'])
def update_song(song_id):
    with tracer.start_as_current_span("update_song") as span:
        logger.info(f"PUT /songs/{song_id} request received")
        span.set_attribute("song_id", song_id)
        SONGS_API_REQUESTS.labels(method='PUT', endpoint='/songs/<song_id>').inc()
        if song_id not in songs:
            span.set_status(trace.status.Status(trace.status.StatusCode.ERROR, "Song not found"))
            abort(404, description="Song not found")

        data = request.get_json()
        songs[song_id] = {
            'id': song_id,
            'title': data['title'],
            'author': data['author'],
            'genre': data['genre'],
            'year': data['year']
        }
        return jsonify(songs[song_id]), 200


@app.route('/songs/<song_id>', methods=['DELETE'])
def delete_song(song_id):
    with tracer.start_as_current_span("delete_song") as span:
        logger.info(f"DELETE /songs/{song_id} request received")
        span.set_attribute("song_id", song_id)
        SONGS_API_REQUESTS.labels(method='DELETE', endpoint='/songs/<song_id>').inc()
        if song_id not in songs:
            span.set_status(trace.status.Status(trace.status.StatusCode.ERROR, "Song not found"))
            abort(404, description="Song not found")

        del songs[song_id]
        return '', 204


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
