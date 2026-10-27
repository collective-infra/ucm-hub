from flask import Flask, Response, jsonify, request, send_from_directory


# ---------------- WEB APP ----------------

def create_app(store, source_label):

    app = Flask(__name__, static_folder="static")

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/api/raw")
    def raw():

        version, body = store.body(source_label)
        etag = f'"{version}"'

        # Nothing new since this browser's last fetch: send no body.
        if etag in request.headers.get("If-None-Match", ""):
            response = Response(status=304)
        else:
            response = Response(body, mimetype="application/json")

        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.route("/healthz")
    def healthz():
        return jsonify(store.stats())

    return app
