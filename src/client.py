import socket
import argparse
import srtp

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
paquet_demande = srtp.create_packet(1, 63, 0, 0, requete_texte)
sock.sendto(paquet_demande, server_addr)


f = open(args.save, "wb")
wanted = 1


while True:
    try:
        data, addr = sock.recvfrom(2000)
        paquet = srtp.parse_packet(data)

        if paquet == None:
            continue

        if paquet['length'] == 0:
            ack_fin = srtp.create_packet(2, 63, (paquet['seqnum'] + 1) % 2048, 0)
            sock.sendto(ack_fin, server_addr)
            break

        if paquet['seqnum'] == wanted:
            f.write(paquet['payload'])
            wanted = (wanted + 1) % 2048

        timestamp_recu = paquet['timestamp']
        ack = srtp.create_packet(2, 63, wanted, timestamp_recu)
        sock.sendto(ack, server_addr)

    except socket.timeout:
        if wanted == 1:
            sock.sendto(paquet_demande, server_addr)
        else:
            sock.sendto(ack, server_addr)

f.close()
sock.close()