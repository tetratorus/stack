"""Check the stack-manager service config for spine-serve and that `spine serve` exposes Gold the way the config expects."""
import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REWIRE = HERE.parent
sys.path.insert(0, str(HERE))


def _spec():
    return json.loads((REWIRE / "services/spine-serve.json").read_text())


def test_service_config_shape():
    s = _spec()
    c = s["ServiceSpec"]["TaskTemplate"]["ContainerSpec"]
    assert s["ServiceSpec"]["Name"] == "spine-serve"
    assert c["Image"].startswith("localhost/")  # built locally, stack-manager will not try to pull it
    mount = c["Mounts"][0]
    assert (mount["Type"], mount["Target"], mount["ReadOnly"]) == ("volume", "/lake", True)
    port = c["Command"][c["Command"].index("--port") + 1]
    assert s["endpoints"]["features"]["url"] == f"http://localhost:{port}/"
    assert c["Command"][c["Command"].index("--lake") + 1] == mount["Target"]
    cfg = json.loads((REWIRE / "stack-config.example.json").read_text())
    assert "spine-serve" in cfg["services"]["includes"] and mount["Source"] in cfg["volumes"]


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _get(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read())


@pytest.fixture()
def served(tmp_path):
    from make_demo_lake import build
    lake = build(tmp_path)
    port = _free_port()
    cmd = _spec()["ServiceSpec"]["TaskTemplate"]["ContainerSpec"]["Command"]
    cmd = [str(lake.root) if a == "/lake" else str(port) if a == "8090" else "127.0.0.1" if a == "0.0.0.0" else a
           for a in cmd]
    cmd[0] = str(Path(sys.executable).with_name("spine"))
    p = subprocess.Popen(cmd)
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            _get(base + "/collections")
            break
        except OSError:
            time.sleep(0.1)
    yield base
    p.terminate()
    p.wait(5)


def test_gold_is_exposed_as_ogc_features(served):
    ids = [c["id"] for c in _get(served + "/collections")["collections"]]
    assert "silver.plots" in ids
    gold = [i for i in ids if i.startswith("gold.demo.plot_capacity")]
    assert gold, ids
    fc = _get(f"{served}/collections/{gold[0]}/items")
    assert fc["type"] == "FeatureCollection" and len(fc["features"]) == 2
    props = {f["properties"]["plot_id"]: f["properties"]["gfa_m2"] for f in fc["features"]}
    assert props == pytest.approx({"P1": 3600 * 2.8, "P2": 2400 * 4.2})
    assert fc["features"][0]["geometry"] is not None  # geometry joined back from the Silver plots hub
