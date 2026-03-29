import struct
import zlib
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import srtp

def test_create_retourne_bytes():
    pkt = srtp.create_packet(1, 0, 0, 0)
    assert isinstance(pkt, bytes)

def test_create_taille_sans_payload():
    pkt = srtp.create_packet(1, 0, 0, 0)
    assert len(pkt) == 12

def test_create_taille_avec_payload():
    pkt = srtp.create_packet(1, 0, 0, 0, b"hello")
    assert len(pkt) == 12 + 5 + 4

def test_create_taille_max_payload():
    pkt = srtp.create_packet(1, 0, 0, 0, b"x" * 1024)
    assert len(pkt) == 12 + 1024 + 4

def test_create_pas_de_crc2_si_payload_vide():
    pkt = srtp.create_packet(1, 0, 0, 0, b"")
    assert len(pkt) == 12

def test_create_timestamp_correct():
    pkt = srtp.create_packet(1, 0, 0, 0xDEADBEEF)
    ts = struct.unpack("!I", pkt[4:8])[0]
    assert ts == 0xDEADBEEF

def test_create_seqnum_max():
    pkt = srtp.create_packet(1, 0, 2047, 0)
    seqnum = struct.unpack("!I", pkt[:4])[0] & 0x7FF
    assert seqnum == 2047

def test_create_seqnum_wraparound():
    pkt = srtp.create_packet(1, 0, 2048, 0)   # 2048 % 2048 == 0
    seqnum = struct.unpack("!I", pkt[:4])[0] & 0x7FF
    assert seqnum == 0

def test_parse_data_aller_retour():
    pkt = srtp.create_packet(1, 10, 5, 999, b"bonjour")
    result = srtp.parse_packet(pkt)
    assert result is not None
    assert result["type"]      == 1
    assert result["window"]    == 10
    assert result["seqnum"]    == 5
    assert result["timestamp"] == 999
    assert result["payload"]   == b"bonjour"
    assert result["length"]    == 7

def test_parse_ack_aller_retour():
    pkt = srtp.create_packet(2, 32, 7, 42)
    result = srtp.parse_packet(pkt)
    assert result is not None
    assert result["type"]    == 2
    assert result["seqnum"]  == 7
    assert result["payload"] == b""

def test_parse_sack_aller_retour():
    pkt = srtp.create_packet(3, 0, 100, 0)
    result = srtp.parse_packet(pkt)
    assert result is not None
    assert result["type"] == 3

def test_parse_paquet_vide_retourne_none():
    assert srtp.parse_packet(b"") is None

def test_parse_trop_court_retourne_none():
    assert srtp.parse_packet(b"A" * 11) is None

def test_parse_crc1_invalide_retourne_none():
    pkt = bytearray(srtp.create_packet(1, 0, 0, 0, b"test"))
    pkt[9] ^= 0xFF   # corrompre CRC1
    assert srtp.parse_packet(bytes(pkt)) is None

def test_parse_crc2_invalide_retourne_none():
    pkt = bytearray(srtp.create_packet(1, 0, 0, 0, b"test"))
    pkt[-1] ^= 0xFF  # corrompre CRC2
    assert srtp.parse_packet(bytes(pkt)) is None

def test_parse_type_zero_retourne_none():
    word = (0 << 30) | (1 << 24) | (0 << 11) | 1
    h = struct.pack("!II", word, 0)
    crc1 = zlib.crc32(h) & 0xFFFFFFFF
    pkt = struct.pack("!III", word, 0, crc1)
    assert srtp.parse_packet(pkt) is None

def test_parse_longueur_trop_grande_retourne_none():
    length = 1025
    word = (1 << 30) | (length << 11)
    h = struct.pack("!II", word, 0)
    crc1 = zlib.crc32(h) & 0xFFFFFFFF
    payload = b"x" * length
    crc2 = zlib.crc32(payload) & 0xFFFFFFFF
    pkt = struct.pack("!III", word, 0, crc1) + payload + struct.pack("!I", crc2)
    assert srtp.parse_packet(pkt) is None

def test_parse_payload_tronque_retourne_none():
    pkt = srtp.create_packet(1, 0, 0, 0, b"donnees")
    assert srtp.parse_packet(pkt[:-1]) is None

def test_parse_longueur_1024_acceptee():
    pkt = srtp.create_packet(1, 0, 0, 0, b"x" * 1024)
    result = srtp.parse_packet(pkt)
    assert result is not None
    assert result["length"] == 1024
