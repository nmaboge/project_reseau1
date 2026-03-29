import os
import socket
import subprocess
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
SERVER = os.path.join(SRC, "server.py")
CLIENT = os.path.join(SRC, "client.py")

LINK_SIM = os.environ.get("LINK_SIM_PATH", os.path.expanduser("~/Desktop/Linksimulator/link_sim"))

TEST_CASES = [
    ("perte_10pct",      ["-l", "10"]),
    ("corruption_5pct",  ["-e", "5"]),
    ("troncature_5pct",  ["-c", "5"]),
    ("delai_200ms",      ["-d", "200", "-j", "50"]),
]


def get_free_port():
    s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    s.bind(("::1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.mark.parametrize("scenario,args", TEST_CASES)
def test_transfert_reseau(scenario, args, tmp_path):
    if not os.path.exists(LINK_SIM):
        pytest.skip(f"link_sim introuvable : {LINK_SIM}. Definir LINK_SIM_PATH si necessaire.")

    srv_port = get_free_port()
    sim_port = get_free_port()

    fichiers = tmp_path / "fichiers"
    fichiers.mkdir()
    contenu = bytes(range(256)) * 8   # 2048 octets
    (fichiers / "data.bin").write_bytes(contenu)

    sim = subprocess.Popen(
        [LINK_SIM, "-p", str(sim_port), "-P", str(srv_port)] + args,
        cwd=os.path.dirname(LINK_SIM),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    time.sleep(0.2)

    srv = subprocess.Popen(
        [sys.executable, SERVER, "::1", str(srv_port), "--root", str(fichiers)],
        cwd=SRC,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    time.sleep(0.2)

    dest = tmp_path / f"recu_{scenario}.bin"
    url = f"http://[::1]:{sim_port}/data.bin"

    try:
        res = subprocess.run(
            [sys.executable, CLIENT, url, "--save", str(dest)],
            cwd=SRC,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=60
        )
        assert res.returncode == 0
        assert dest.read_bytes() == contenu

    finally:
        for proc in [srv, sim]:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
