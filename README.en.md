# Rhine Two-City Itinerary Maps

[Chinese](README.md) | English

Public, interactive itinerary maps for **Dusseldorf and Cologne**, built with
locally bundled Leaflet assets, Flask, and Gunicorn. The application runs on
**Azure App Service for Linux**, not Azure Static Web Apps. No Node.js or frontend
build step is required.

**Deployment URLs:** [Home](https://rhine-trip-maps-columbia-z.azurewebsites.net/) |
[Dusseldorf](https://rhine-trip-maps-columbia-z.azurewebsites.net/dusseldorf.html) |
[Cologne](https://rhine-trip-maps-columbia-z.azurewebsites.net/cologne.html).
Availability depends on the deployment status.

The map interface and itinerary text are currently in Chinese; this README
provides English project documentation.

## Features

- Flag markers with place details and suggested visit times.
- Per-day filters, walking routes, and schematic public transport connections.
- Links to external walking and transit directions.
- Transport budget estimates, source links, and planning caveats.
- A downloadable, portable ZIP containing both city maps.

Visiting `/` redirects to `/dusseldorf.html`; the other city is available at
`/cologne.html`. Use the download button to retrieve `/trip-maps.zip`, extract it,
and open either city HTML file directly.

The ZIP includes the scripts, styles, and route data. **OpenStreetMap basemap
tiles and external navigation still require an internet connection.** If tiles
cannot load, the page displays a warning; markers and route data remain
available. The archive does not contain a copy of itself, so use the online site
to download a fresh ZIP.

## Itinerary and data caveats

| Date | Plan |
| --- | --- |
| September 19, 2026 | Arrive at Dusseldorf Airport (DUS) around noon; stay one night in Dusseldorf. |
| September 20 | Travel to Cologne; stay the nights of September 20 and 21. |
| September 22 | Check out and depart Cologne Bonn Airport (CGN) at 23:15 for Dublin. Arrival may be after midnight on September 23; check the ticket. |

Unless explicitly identified as Dublin local time, itinerary times use German
local time. Hotel markers indicate **suggested accommodation areas, not booked
hotels**. Check train schedules, opening hours, flights, and fares with official
providers before travel.

The estimated transport budget is **EUR 40-50 per person**, excluding flights,
accommodation, and attraction admission. The intercity fare is a budgeting range,
not a verified quote for specific stops. Do not buy additional tickets for
journeys already covered by a valid pass.

The current itinerary contains 17 walking legs, with a maximum length of
999 metres. **Keeping each leg within 1 km does not mean walking only 1 km per
day.** These distances exclude walking inside museums and stations, access to an
actual hotel, and temporary diversions. Public transport lines on the maps are
schematic connections, not live navigation or exact track geometry.

OpenStreetMap attribution and data sources are retained. Leaflet's BSD 2-Clause
license is included in
[`public/LEAFLET-LICENSE.txt`](public/LEAFLET-LICENSE.txt).
The repository does not include booking records, personal profile data,
source-data caches, or booked hotel details. Keep future changes within this
public-content boundary.

## Run locally

Python 3.12 is recommended. The application also supports Python 3.11, and CI
covers both versions. From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
gunicorn --bind=127.0.0.1:8000 --timeout 120 app:app
```

Open `http://127.0.0.1:8000/`. Press Ctrl-C to stop the server.
Gunicorn runs on Linux and macOS; Windows users can use WSL. Do not use the Flask
development server or debug mode in production.

```sh
python -m unittest discover -s tests -v
curl --fail http://127.0.0.1:8000/healthz
```

`GET /healthz` returns `{"status":"ok"}`. It checks application responsiveness,
not third-party basemap availability, transport schedules, or other external
services. HEAD requests are supported. Health responses are not cached; static
assets are revalidated using ETags.

Only the nine explicitly allowlisted files under `public/` are served. Directory
listing, server source, configuration files, and repository files are not
exposed.

## Update the maps and downloadable ZIP

After editing the public assets under `public/`, run these commands from a
virtual environment with the project dependencies installed:

```sh
python -m scripts.build_zip
python -m scripts.build_zip --check
python -m unittest discover -s tests -v
```

Commit the updated assets and `public/trip-maps.zip` together. The portable
archive contains only:

- `dusseldorf.html` and `cologne.html`
- `app.js` and `data.js`
- `style.css`
- `leaflet.js`, `leaflet.css`, and `LEAFLET-LICENSE.txt`

It does not recursively include itself, server code, source-data caches, or
credentials. File order, timestamps, and permissions are fixed. Entries use
uncompressed ZIP storage so identical inputs produce byte-for-byte identical
archives across Python and zlib versions.

Tests check that the ZIP matches the public files, itinerary facts remain
consistent, route references are valid, and all walking legs stay within the
1,000-metre limit. Update the corresponding assertions when intentionally
changing the itinerary.

## Azure App Service configuration

An administrator configures the Azure resources and deployment identity outside
the repository. The workflow **does not create resources, change billing
settings, or configure credentials**.

| Setting | Requirement |
| --- | --- |
| Hosting | Azure App Service, Linux B1, Central US |
| Python runtime | `PYTHON\|3.12` |
| Startup command | `gunicorn --bind=0.0.0.0:8000 --timeout 120 app:app` |
| Application setting | `SCM_DO_BUILD_DURING_DEPLOYMENT=true` |
| Availability | Enable HTTPS Only and Always On; use `/healthz` as the health check path. |

Deployment uses ZIP Deploy with a remote Oryx build. Oryx installs the
Linux/Python 3.12 dependencies from `requirements.txt` at the archive root.
Do not upload a local `.venv` or `.python_packages` directory.

Do not enable `WEBSITE_RUN_FROM_PACKAGE`; it is incompatible with the remote
build approach used here. In the startup command, `app:app` refers to the Flask
WSGI object in the root-level `app.py`.

Configure the following GitHub repository **variables** under
**Settings > Secrets and variables > Actions > Variables**:

| Variable | Purpose |
| --- | --- |
| `AZURE_CLIENT_ID` | Client ID of the deployment identity |
| `AZURE_TENANT_ID` | Tenant containing that identity |
| `AZURE_SUBSCRIPTION_ID` | Target subscription |
| `AZURE_WEBAPP_NAME` | Name of the existing App Service application |

Grant the deployment identity the minimum permissions needed for the target
application and configure its GitHub OIDC federated identity credential:

| Field | Value |
| --- | --- |
| Issuer | `https://token.actions.githubusercontent.com` |
| Audience | `api://AzureADTokenExchange` |
| Current subject for this repository | `repo:Columbia-Z@173833594/rhine-trip-maps@1360641122:ref:refs/heads/main` |

The subject currently issued for this repository includes immutable account and
repository IDs. Match the `subject claim` shown in the `azure/login` logs
**exactly**; do not assume the older format without IDs. When adapting this
project to another repository, use the subject actually issued for that
repository.

This workflow does not use a GitHub environment. If an environment is added
later, update the federated subject accordingly. No publish profile, client
secret, or interactive user login is required for the workflow. Never commit
those credentials.

## Costs and stopping charges

The public pay-as-you-go price for a single Linux B1 instance in Central US is
**USD 0.018 per hour**, approximately **USD 13.14 for 730 hours**. Bandwidth,
taxes, and other applicable charges are additional. This is an estimate;
actual costs depend on Azure's current pricing and billing. **It does not
confirm the subscription's remaining credit balance.**

**Stopping the Web App does not stop App Service Plan charges.** When the
deployment is no longer needed, first confirm that the resources and their
dependencies can be removed, then delete the dedicated App Service Plan or the
entire dedicated resource group. Deleting a resource group also deletes its
other resources. Neither this repository nor its deployment workflow performs
these deletions automatically.

## Deployment workflow

`.github/workflows/azure.yml` runs Python 3.11 and 3.12 tests on pull requests,
pushes to `main`, and manual dispatches.

Deployment runs only after all tests pass, on a **push to `main` or a
`workflow_dispatch` targeting `main`**. Pull requests and manual runs targeting
other branches do not receive deployment tokens. Only the deployment job has
`id-token: write`; the other permission is `contents: read`. Actions are pinned
to specific commits.

If any required Azure variable is missing, the workflow reports an explicit
error and stops rather than guessing an application name or credentials.

The workflow uses `azure/login` with OIDC and `azure/webapps-deploy`.
To inspect the same deployment package locally:

```sh
python -m scripts.build_zip --deployment
python -m zipfile -l dist/app-service.zip
```

The deployment archive contains only `app.py`, `requirements.txt`, and the
allowlisted `public/` files, including the portable `trip-maps.zip`. Files sit at
the ZIP root without an extra parent directory. Tests, maintenance scripts, and
repository configuration are excluded.

`dist/` and deployment archives are ignored by Git; do not commit them. Packaging
fails if the portable ZIP is out of date.

Once Azure and the repository variables are configured, merging a pull request
into `main` triggers deployment. Alternatively, open the workflow in GitHub
Actions, choose **Run workflow**, and select `main`.

After deployment, open `/healthz`, both city pages, and the download link on the
application URL. If deployment fails, first check the Actions logs for missing
variables, OIDC mismatches, or deployment errors. Then inspect App Service's
deployment and startup logs, checking the runtime, startup command, and Oryx
settings.
