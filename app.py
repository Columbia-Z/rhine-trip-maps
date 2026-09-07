from pathlib import Path

from flask import Flask, abort, redirect, send_from_directory, url_for


PUBLIC_DIR = Path(__file__).resolve().parent / "public"
PORTABLE_ASSETS = (
    "dusseldorf.html",
    "cologne.html",
    "app.js",
    "data.js",
    "style.css",
    "leaflet.js",
    "leaflet.css",
    "LEAFLET-LICENSE.txt",
)
DOWNLOAD_NAME = "trip-maps.zip"
PUBLIC_ASSETS = (*PORTABLE_ASSETS, DOWNLOAD_NAME)

app = Flask(__name__, static_folder=None)


@app.get("/")
def index():
    return redirect(url_for("public_asset", filename="dusseldorf.html"))


@app.get("/healthz")
def health():
    return {"status": "ok"}, 200, {"Cache-Control": "no-store"}


@app.get("/<path:filename>")
def public_asset(filename):
    if filename not in PUBLIC_ASSETS:
        abort(404)
    return send_from_directory(
        PUBLIC_DIR,
        filename,
        as_attachment=filename == DOWNLOAD_NAME,
        conditional=True,
        max_age=0,
    )


@app.errorhandler(404)
def not_found(error):
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        "<title>404 - Not found</title><h1>404 - Not found</h1>"
        '<p><a href="/">Return to the itinerary maps</a></p></html>',
        404,
    )


@app.after_request
def response_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Leaflet positions its layers with inline styles; scripts stay same-origin.
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https://tile.openstreetmap.org; "
        "font-src 'self'; connect-src 'self'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
    )
    return response
