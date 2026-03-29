import os
import sys
import subprocess
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
SERVER = os.path.join(SRC, "server.py")
CLIENT = os.path.join(SRC, "client.py")


def get_free_port():
    import socket
    s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    s.bind(("::1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def lancer_client(port, fichier, dest, timeout=10):
    url = f"http://::1:{port}/{fichier}"
    subprocess.run(
        [sys.executable, CLIENT, url, "--save", str(dest)],
        cwd=SRC, capture_output=True, timeout=timeout
    )
    return open(dest, "rb").read() if os.path.exists(dest) else b""


@pytest.fixture
def serveur(tmp_path):
    port = get_free_port()
    dossier = tmp_path / "root"
    dossier.mkdir()
    srv = subprocess.Popen(
        [sys.executable, SERVER, "::1", str(port), "--root", str(dossier)],
        cwd=SRC, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    time.sleep(0.2)
    yield port, dossier
    srv.terminate()
    srv.wait()


def test_petit_fichier(tmp_path, serveur):
    port, dossier = serveur
    contenu = b"bonjour le monde"
    (dossier / "petit.txt").write_bytes(contenu)
    recu = lancer_client(port, "petit.txt", tmp_path / "petit.txt")
    assert recu == contenu


def test_fichier_un_bloc(tmp_path, serveur):
    port, dossier = serveur
    contenu = b"x" * 1024
    (dossier / "bloc.bin").write_bytes(contenu)
    recu = lancer_client(port, "bloc.bin", tmp_path / "bloc.bin")
    assert recu == contenu


def test_fichier_multi_blocs(tmp_path, serveur):
    port, dossier = serveur
    contenu = b"y" * 5120
    (dossier / "gros.bin").write_bytes(contenu)
    recu = lancer_client(port, "gros.bin", tmp_path / "gros.bin")
    assert recu == contenu


def test_fichier_binaire(tmp_path, serveur):
    port, dossier = serveur
    contenu = bytes(range(256)) * 4
    (dossier / "binaire.bin").write_bytes(contenu)
    recu = lancer_client(port, "binaire.bin", tmp_path / "binaire.bin")
    assert recu == contenu


def test_fichier_inexistant(tmp_path, serveur):
    port, _ = serveur
    recu = lancer_client(port, "nexistepas.bin", tmp_path / "vide.bin")
    assert recu == b""