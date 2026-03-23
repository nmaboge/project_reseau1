import socket
import argparse
import srtp
import time

parser = argparse.ArgumentParser()
parser.add_argument("servername")
parser.add_argument("--save", default="llm.model")
args = parser.parse_args()
url = args.servername.replace("http://", "")
ip_port, fichier_demande = url.split("/", 1)
ip = ip_port.rsplit(":", 1)[0]
port = int(ip_port.rsplit(":", 1)[1])
server_addr = (ip, port)

sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
sock.settimeout(2.0)

requete_texte = f"GET /{fichier_demande}".encode('ascii')
ts_initial = int(time.monotonic() * 1000) & 0xFFFFFFFF
paquet_demande = srtp.create_packet(1, 32, 0, ts_initial, requete_texte)
sock.sendto(paquet_demande, server_addr)

f = open(args.save, "wb")
wanted = 1
buffer_reception = {} 
MAX_WINDOW = 32

while True:
    try:
        data, addr = sock.recvfrom(2000)
        paquet = srtp.parse_packet(data)

        if paquet is None:
            continue

        if paquet['length'] == 0:
            ack_fin = srtp.create_packet(2, 0, (paquet['seqnum'] + 1) % 2048, 0)
            sock.sendto(ack_fin, addr)
            break

        seq_recu = paquet['seqnum']

        if seq_recu >= wanted or (wanted > 1500 and seq_recu < 500):
            if seq_recu not in buffer_reception:
                buffer_reception[seq_recu] = paquet['payload']

        while wanted in buffer_reception:
            payload_a_ecrire = buffer_reception.pop(wanted)
            f.write(payload_a_ecrire)
            wanted = (wanted + 1) % 2048

        current_window = max(0, MAX_WINDOW - len(buffer_reception))

        ack = srtp.create_packet(2, current_window, wanted, paquet['timestamp'])
        sock.sendto(ack, addr)

    except socket.timeout:
        if wanted == 1:
            sock.sendto(paquet_demande, server_addr)
        else:
            if 'ack' in locals():
                sock.sendto(ack, server_addr)

f.close()
sock.close()