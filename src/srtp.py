import struct
import zlib

PTYPE_DATA = 1
PTYPE_ACK = 2
PTYPE_SACK = 3

def create_packet(ptype, window, seqnum, timestamp, payload=b""):
    length = len(payload)
    
    ptype = ptype & 0x3
    window = window & 0x3F
    length = length & 0x1FFF
    seqnum = seqnum & 0x7FF
    
    data_32bits = (ptype << 30) | (window << 24) | (length << 11) | seqnum
    
    h_hash = struct.pack('!II', data_32bits, timestamp)
    crc1 = zlib.crc32(h_hash) & 0xffffffff
    
    h = struct.pack('!III', data_32bits, timestamp, crc1)
    packet = bytearray(h + payload)
    
    if length > 0:
        crc2 = zlib.crc32(payload) & 0xffffffff
        packet += struct.pack('!I', crc2)
        
    return bytes(packet)

def parse_packet(packet_bytes):

    if len(packet_bytes) < 12:
        return None
        
    data_32bits, timestamp, crc1_recevied = struct.unpack('!III', packet_bytes[:12])
    
    h_hash = struct.pack('!II', data_32bits, timestamp) 
    check_crc1 = zlib.crc32(h_hash) & 0xffffffff
    
    if crc1_recevied != check_crc1:
        return None
        
    ptype = (data_32bits >> 30) & 0x3

    if ptype == 0:
        return None

    window = (data_32bits >> 24) & 0x3F
    length = (data_32bits >> 11) & 0x1FFF

    if length > 1024:
        return None
    
    seqnum = data_32bits & 0x7FF
    
    payload = b""
    if length > 0:
        if len(packet_bytes) < 12 + length + 4:
            return None
            
        payload = packet_bytes[12:12+length]
        crc2_received = struct.unpack('!I', packet_bytes[12+length:12+length+4])[0]
        
        if (zlib.crc32(payload) & 0xffffffff) != crc2_received:
            return None
            
    return {
        'type': ptype,
        'window': window,
        'length': length,
        'seqnum': seqnum,
        'timestamp': timestamp,
        'payload': payload
    }