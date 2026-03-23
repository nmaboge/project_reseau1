import socket
import argparse
import os
import srtp


parse = argparse.ArgumentParser()
parse.add_argument("hostname")
parse.add_argument("port", type=int)
parse.add_argument("--root", default=".")
args = parse.parse_args()


sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
sock.bind((args.hostname, args.port))


while True:
    sock.settimeout(None)
    data, client_addr = sock.recvfrom(2000)
    paquet = srtp.parse_packet(data)

    if paquet == None:
        continue

    if paquet['type'] == 1 and paquet['seqnum'] == 0:
        texte_recu = paquet['payload'].decode('ascii')
        
        filesname = texte_recu.split(" ")[1]
        
        if filesname.startswith("/"):
            filesname = filesname[1:]
            
        path = os.path.join(args.root, filesname)

        if not os.path.exists(path):
            paquet_vide = srtp.create_packet(1, 63, 1, 0)
            sock.sendto(paquet_vide, client_addr)
            continue

        f = open(path, "rb")
        seq = 1

        while True:
            paquet = f.read(1024)
            if not paquet:
                break

            paquet_donnee = srtp.create_packet(1, 63, seq, 0, paquet)
            

            received = False
            while received == False:
                sock.sendto(paquet_donnee, client_addr)
                sock.settimeout(1.0)
                
                try:
                    ack_data, _ = sock.recvfrom(2000)
                    ack_paquet = srtp.parse_packet(ack_data)
                    
                    if ack_paquet != None and ack_paquet['type'] == 2:
                        prochain_attendu = (seq + 1) % 2048
                        if ack_paquet['seqnum'] == prochain_attendu:
                            received = True
                            seq = prochain_attendu
                except socket.timeout:
                    pass

        f.close()
        
        paquet_fin = srtp.create_packet(1, 63, seq, 0)
        sock.sendto(paquet_fin, client_addr)