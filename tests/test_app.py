import unittest

from app import DOWNLOAD_NAME, PUBLIC_ASSETS, PUBLIC_DIR, app


class AppTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_root_redirects_to_dusseldorf(self):
        with self.client.get("/") as response:
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers["Location"], "/dusseldorf.html")
        with self.client.get("/", follow_redirects=True) as response:
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'data-city="dusseldorf"', response.data)

    def test_health(self):
        with self.client.get("/healthz") as response:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, {"status": "ok"})
            self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_both_city_pages(self):
        for city in ("dusseldorf", "cologne"):
            with self.subTest(city=city), self.client.get(f"/{city}.html?day=20") as response:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, "text/html")
                self.assertIn(f'data-city="{city}"'.encode(), response.data)
                for asset in ("leaflet.css", "style.css", "leaflet.js", "data.js", "app.js"):
                    self.assertIn(f'"{asset}"'.encode(), response.data)

    def test_all_public_assets(self):
        for name in PUBLIC_ASSETS:
            with self.subTest(name=name), self.client.get(f"/{name}") as response:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, (PUBLIC_DIR / name).read_bytes())
                if name.endswith(".css"):
                    self.assertEqual(response.mimetype, "text/css")
                elif name.endswith(".js"):
                    self.assertIn(response.mimetype, ("text/javascript", "application/javascript"))
                elif name == DOWNLOAD_NAME:
                    self.assertEqual(response.mimetype, "application/zip")
                    self.assertEqual(
                        response.headers["Content-Disposition"],
                        f"attachment; filename={DOWNLOAD_NAME}",
                    )

    def test_head_and_conditional_requests(self):
        with self.client.head("/data.js") as response:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b"")
            self.assertEqual(response.content_length, (PUBLIC_DIR / "data.js").stat().st_size)
            etag = response.headers["ETag"]
        with self.client.get("/data.js", headers={"If-None-Match": etag}) as response:
            self.assertEqual(response.status_code, 304)
            self.assertIn("max-age=0", response.headers["Cache-Control"])

    def test_download_supports_range_requests(self):
        with self.client.get(f"/{DOWNLOAD_NAME}", headers={"Range": "bytes=0-31"}) as response:
            self.assertEqual(response.status_code, 206)
            self.assertEqual(response.data, (PUBLIC_DIR / DOWNLOAD_NAME).read_bytes()[:32])

    def test_private_and_unknown_paths_are_not_served(self):
        paths = (
            "/missing", "/missing.html", "/favicon.ico", "/public/", "/public/data.js",
            "/static/data.js", "/app.py", "/requirements.txt", "/README.md", "/.gitignore",
            "/.git/config", "/.env", "/.azure/config", "/.venv/pyvenv.cfg",
            "/.github/workflows/azure.yml", "/scripts/build_zip.py", "/tests/test_app.py",
            "/dist/app-service.zip", "/build_maps.py", "/source-cache/",
            "/../app.py", "/%2e%2e/app.py", "/%2e%2e%2fapp.py",
            "/public/../../app.py", "/public/%2e%2e/app.py", "/public%2f..%2fapp.py",
            "/..%5capp.py", "/%252e%252e%252fapp.py", "/data.js/../app.py",
            "/data.js%00", "/etc/passwd",
        )
        for path in paths:
            with self.subTest(path=path), self.client.get(path) as response:
                self.assertEqual(response.status_code, 404)
                self.assertIn(b"Return to the itinerary maps", response.data)
                self.assertNotIn(str(PUBLIC_DIR.parent).encode(), response.data)

    def test_writes_are_not_supported(self):
        for path in ("/", "/healthz", "/data.js"):
            with self.subTest(path=path), self.client.post(path) as response:
                self.assertEqual(response.status_code, 405)

    def test_headers_allow_map_tiles_but_not_external_scripts(self):
        for path in ("/", "/healthz", "/dusseldorf.html", "/missing"):
            with self.subTest(path=path), self.client.get(path) as response:
                self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
                self.assertEqual(
                    response.headers["Referrer-Policy"], "strict-origin-when-cross-origin"
                )
                policy = response.headers["Content-Security-Policy"]
                self.assertIn("script-src 'self';", policy)
                self.assertIn("https://tile.openstreetmap.org", policy)
                self.assertIn("style-src 'self' 'unsafe-inline';", policy)
                self.assertIn("frame-ancestors 'none';", policy)


if __name__ == "__main__":
    unittest.main()
