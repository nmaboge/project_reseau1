import socket
import argparse
import os
import srtp
import time

parse = argparse.ArgumentParser()
parse.add_argument("hostname")
parse.add_argument("port", type=int)
parse.add_argument("--root", default=".")
args = parse.parse_args()

sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
sock.bind((args.hostname, args.port))

INITIAL_RTO = 1.0

while True:
    sock.settimeout(None)
    data, client_addr = sock.recvfrom(2000)
    paquet = srtp.parse_packet(data)

    if paquet is None or paquet['type'] != 1 or paquet['seqnum'] != 0:
        continue

    texte_recu = paquet['payload'].decode('ascii')
    parts = texte_recu.split(" ")
    if len(parts) < 2: continue
    filename = parts[1].lstrip("/")
    path = os.path.join(args.root, filename)

    if not os.path.exists(path):
        paquet_vide = srtp.create_packet(1, 63, 1, 0, b"")
        sock.sendto(paquet_vide, client_addr)
        continue

    f = open(path, "rb")
    window_size = 1
    base = 1
    next_seq = 1

    packets_in_flight = {}
    rto = INITIAL_RTO
    finished_reading = False

    sock.settimeout(0.01)

    while not finished_reading or packets_in_flight:
        while not finished_reading and len(packets_in_flight) < window_size:
            data_chunk = f.read(1024)
            if not data_chunk:
                finished_reading = True
                break
            
            t_send = time.monotonic()
            pkt = srtp.create_packet(1, 63, next_seq, int(t_send * 1000) & 0xFFFFFFFF, data_chunk)
            
            packets_in_flight[next_seq] = {
                'data': pkt,
                't_send': t_send,
                'retransmitted': False
            }
            
            sock.sendto(pkt, client_addr)
            next_seq = (next_seq + 1) % 2048

        try:
            ack_data, _ = sock.recvfrom(2000)
            ack_paquet = srtp.parse_packet(ack_data)
            
            if ack_paquet and (ack_paquet['type'] == 2 or ack_paquet['type'] == 3):
                ack_num = ack_paquet['seqnum']
                window_size = max(1, ack_paquet['window'])

                to_remove = [s for s in packets_in_flight if s < ack_num] 

                if ack_num < base:
                    to_remove = [s for s in packets_in_flight if s >= base or s < ack_num]
                
                for s in to_remove:
                    del packets_in_flight[s]
                
                base = ack_num

        except socket.timeout:
            pass

        now = time.monotonic()
        for s, p_info in packets_in_flight.items():
            if now - p_info['t_send'] > rto:
                p_info['t_send'] = now
                p_info['retransmitted'] = True
                sock.sendto(p_info['data'], client_addr)
                rto = min(60.0, rto * 2.0)

    f.close()
    paquet_fin = srtp.create_packet(1, 63, next_seq, 0, b"")
    sock.sendto(paquet_fin, client_addr)