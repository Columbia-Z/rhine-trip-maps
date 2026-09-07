from collections import Counter
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from app import DOWNLOAD_NAME, PORTABLE_ASSETS, PUBLIC_ASSETS, PUBLIC_DIR
from scripts.build_zip import archive_bytes, deployment_zip, portable_zip


class AssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (PUBLIC_DIR / "data.js").read_text(encoding="utf-8")
        prefix = "window.TRIP_DATA = "
        if not source.startswith(prefix) or not source.strip().endswith(";"):
            raise ValueError("Expected data.js to contain a single TRIP_DATA JSON assignment")
        cls.data = json.loads(source[len(prefix):].strip()[:-1])

    def test_public_directory_has_only_approved_files(self):
        self.assertEqual({path.name for path in PUBLIC_DIR.iterdir()}, set(PUBLIC_ASSETS))
        self.assertTrue(all(path.is_file() and not path.is_symlink() for path in PUBLIC_DIR.iterdir()))

    def test_itinerary_dates_and_airports(self):
        data = self.data
        self.assertEqual(data["title"], "杜塞尔多夫与科隆 · 2026/9/19–22")
        self.assertEqual(set(data["days"]), {"19", "20", "21", "22"})
        self.assertEqual(data["cities"]["dusseldorf"]["days"], ["19", "20"])
        self.assertEqual(data["cities"]["cologne"]["days"], ["20", "21", "22"])
        self.assertIn("1 晚", data["cities"]["dusseldorf"]["stay"])
        self.assertIn("2 晚", data["cities"]["cologne"]["stay"])
        points = {point["id"]: point for point in data["points"]}
        self.assertIn("9/19 中午抵达", points["d-airport"]["note"])
        self.assertIn("9/22 23:15", points["c-airport"]["note"])
        self.assertIn("9/23 00:10", points["c-airport"]["note"])
        self.assertIn("都柏林当地时间", points["c-airport"]["note"])
        for city in data["cities"].values():
            self.assertIn("非已订酒店", city["hotelNote"])

    def test_route_references_and_geometries(self):
        data = self.data
        points = {point["id"]: point for point in data["points"]}
        self.assertEqual(len(points), 19)
        self.assertEqual(len(data["legs"]), 25)
        self.assertEqual(len({leg["id"] for leg in data["legs"]}), 25)
        self.assertEqual(
            Counter(leg["mode"] for leg in data["legs"]),
            {"walk": 17, "transit": 5, "rail": 2, "intercity": 1},
        )
        for point in points.values():
            self.assertIn(point["city"], data["cities"])
        for leg in data["legs"]:
            with self.subTest(leg=leg["id"]):
                self.assertIn(leg["from"], points)
                self.assertIn(leg["to"], points)
                self.assertIn(leg["day"], data["days"])
                self.assertTrue(leg["depart"])
                self.assertTrue(leg["arrival"])
                self.assertGreaterEqual(len(leg["geometry"]), 2)
                for latitude, longitude in leg["geometry"]:
                    self.assertTrue(-90 <= latitude <= 90)
                    self.assertTrue(-180 <= longitude <= 180)
                if leg["mode"] == "walk":
                    self.assertGreater(leg["distance"], 0)
                    self.assertLessEqual(leg["distance"], 1000)
                    self.assertGreater(leg["duration"], 0)
                    self.assertGreater(len(leg["geometry"]), 2)
                else:
                    self.assertEqual(len(leg["geometry"]), 2)
                    self.assertIsNone(leg["distance"])
                    self.assertTrue(leg["note"])
        self.assertEqual(
            max(leg["distance"] for leg in data["legs"] if leg["mode"] == "walk"), 999
        )

    def test_budget_sources_and_disclaimers_are_preserved(self):
        self.assertEqual(len(self.data["budget"]), 4)
        self.assertEqual(self.data["budget"][-1]["value"], "€40–50")
        self.assertEqual(len(self.data["sources"]), 5)
        self.assertEqual(len(self.data["notes"]), 7)
        for source in self.data["sources"]:
            self.assertTrue(source["url"].startswith("https://"))
        javascript = (PUBLIC_DIR / "app.js").read_text(encoding="utf-8")
        self.assertIn("https://www.openstreetmap.org/copyright", javascript)
        self.assertIn("contributors", javascript)
        license_text = (PUBLIC_DIR / "LEAFLET-LICENSE.txt").read_text(encoding="utf-8")
        self.assertIn("BSD 2-Clause License", license_text)
        self.assertIn("Volodymyr Agafonkin", license_text)

    def test_portable_zip_is_current_reproducible_and_allowlisted(self):
        content = portable_zip()
        self.assertEqual(content, portable_zip())
        self.assertEqual(content, (PUBLIC_DIR / DOWNLOAD_NAME).read_bytes())
        with ZipFile(BytesIO(content)) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(archive.namelist(), sorted(PORTABLE_ASSETS))
            for entry in archive.infolist():
                self.assertEqual(entry.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(archive.read(entry), (PUBLIC_DIR / entry.filename).read_bytes())

    def test_deployment_zip_layout(self):
        content = deployment_zip()
        self.assertEqual(content, deployment_zip())
        with ZipFile(BytesIO(content)) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(
                set(archive.namelist()),
                {"app.py", "requirements.txt"} | {f"public/{name}" for name in PUBLIC_ASSETS},
            )
            for entry in archive.infolist():
                self.assertEqual(
                    archive.read(entry), (PUBLIC_DIR.parent / entry.filename).read_bytes()
                )

    def test_deployment_rejects_stale_portable_zip(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "public").mkdir()
            for name in PORTABLE_ASSETS:
                (root / "public" / name).write_bytes((PUBLIC_DIR / name).read_bytes())
            (root / "public" / DOWNLOAD_NAME).write_bytes(b"stale")
            with self.assertRaisesRegex(ValueError, "Portable ZIP is stale"):
                deployment_zip(root)

    def test_archive_metadata_does_not_depend_on_source_permissions_or_time(self):
        import os

        with TemporaryDirectory() as directory:
            path = Path(directory) / "asset.txt"
            path.write_bytes(b"public")
            first = archive_bytes({"asset.txt": path})
            path.chmod(0o600)
            os.utime(path, (1_700_000_000, 1_700_000_000))
            self.assertEqual(first, archive_bytes({"asset.txt": path}))

    def test_archive_rejects_missing_files_and_symlinks(self):
        with TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            with self.assertRaisesRegex(ValueError, "regular file"):
                archive_bytes({"missing": missing})
            link = Path(directory) / "link"
            link.symlink_to(PUBLIC_DIR / "data.js")
            with self.assertRaisesRegex(ValueError, "regular file"):
                archive_bytes({"data.js": link})

    def test_public_assets_do_not_contain_local_paths_or_private_artifact_names(self):
        forbidden = (
            b"/Users/", b"/home/", b".copilot/session-state", b"build_maps.py",
            b"source-cache", b"BEGIN PRIVATE KEY", b"AZURE_CLIENT_ID",
        )
        for name in PORTABLE_ASSETS:
            content = (PUBLIC_DIR / name).read_bytes()
            for marker in forbidden:
                with self.subTest(asset=name, marker=marker):
                    self.assertNotIn(marker, content)


if __name__ == "__main__":
    unittest.main()
