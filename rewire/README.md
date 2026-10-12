# rewire/ — expose sg-urban-spine Gold through a TWA stack

[sg-urban-spine](https://github.com/tetratorus/sg-urban-spine) keeps model results as **Gold** tables in a lake (GeoParquet).
They are published by Write-Audit-Publish, and each one carries OpenLineage-style lineage. `spine serve` is the spine's
**view** layer: it serves Silver and published Gold as OGC API Features (GeoJSON, EPSG:4326). Here it runs as a
stack-manager custom container, which puts the spine's Gold at `http://localhost:3838/spine/` next to GeoServer, Ontop and the
agents. The service reads the lake **read-only**. It does not copy Gold into the stack or recompute it. No stack-manager code
is changed.

| File | What it is |
|---|---|
| `services/spine-serve.json` | Stack-manager service config. Copy it to `stack-manager/inputs/config/services/`. |
| `stack-config.example.json` | Stack config snippet: include `spine-serve`, populate volume `spine-lake` |
| `Dockerfile` | Builds `localhost/sg-urban-spine-serve:0.1.0` (`pip install git+https://github.com/tetratorus/sg-urban-spine@main`) |
| `tests/` | pytest: checks the config's shape, then runs the config's own `Command` on a demo lake and reads Gold back as features |

## Setup
```bash
docker build -t localhost/sg-urban-spine-serve:0.1.0 stack/rewire      # 'localhost/' tag => stack-manager won't pull
# Docker Hub rate-limited?  add: --build-arg BASE=mirror.gcr.io/library/python:3.11-slim
cp stack/rewire/services/spine-serve.json stack-manager/inputs/config/services/
cp -r /path/to/lake stack-manager/inputs/data/spine-lake                 # the spine lake (silver/ gold/ ...)
# merge stack-config.example.json into stack-manager/inputs/config/<STACK NAME>.json, then
./stack.sh start <STACK NAME>
curl http://localhost:3838/spine/collections                            # silver.* and gold.<transform_id>.<table>
curl http://localhost:3838/spine/collections/gold.gfa.allowable.<table>/items
```
Stack-manager copies `inputs/data/spine-lake` into the volume each time it runs. To refresh Gold, re-run the spine workflow
and then the stack-manager. A bind mount (`"Type": "bind"`) to the live lake also works for development.

## Second route: Gold into PostGIS / Ontop (for KG agents)
Agents that want SPARQL rather than OGC Features can load a Gold table with stack-data-uploader as a `vector` dataset. GDAL ≥ 3.5
reads GeoParquet directly; otherwise export the table to GeoPackage first. Map it with Ontop. TheWorldAvatar
`rewire/agents/gfa_allowable.obda` does this for `gfa.allowable` → `ontoplot:hasMaximumPermittedGFA`. **This route was not run
here** (no stack data).

## What was verified
- `python -m pytest rewire/tests` passes (2 tests). The serve test runs exactly the `Command` from `spine-serve.json`, with the
  lake path and port swapped for a temp lake. It confirms that a published Gold table is listed under `/collections` and that its
  items come back with geometry joined from the Silver `plots` hub.
- The Docker image was built and run with a demo lake mounted read-only (see PR description).
- **Not run:** a full `stack.sh start` with stack-manager/nginx. That needs the stack images and a Docker Swarm, and the test
  environment had neither the Singapore data nor Maven credentials. Known gap: `spine serve` returns absolute `/collections/...`
  links, so behind the `/spine/` prefix clients should prepend it. The spine should honour `X-Forwarded-Prefix`.
