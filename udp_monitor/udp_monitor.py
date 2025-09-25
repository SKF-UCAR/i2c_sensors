import argparse
import binascii
import datetime
import socket
import sys

#!/usr/bin/env python3
"""
Simple UDP monitor: print everything that arrives to address:port.

Usage:
    python udp_mon.py --host 0.0.0.0 --port 9999
"""


BUFFER_SIZE = 65535

def hexdump(data: bytes) -> str:
        hex_str = binascii.hexlify(data).decode('ascii')
        return ' '.join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))

def run(host: str, port: int):
        # create UDP socket (IPv4/IPv6 auto-detect by getaddrinfo)
        infos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_DGRAM, 0, socket.AI_PASSIVE)
        if not infos:
                raise SystemExit("Cannot resolve address")
        af, socktype, proto, _, sockaddr = infos[0]
        sock = socket.socket(af, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(sockaddr)
        print(f"Listening on {host}:{port} (family={af}) - press Ctrl-C to stop")
        try:
                while True:
                        data, addr = sock.recvfrom(BUFFER_SIZE)
                        ts = datetime.datetime.now().isoformat(sep=' ')
                        src = f"{addr[0]}:{addr[1]}" if len(addr) >= 2 else str(addr)
                        text = data.decode('utf-8', errors='replace')
                        hexed = hexdump(data)
                        print(f"[{ts}] from {src} ({len(data)} bytes)")
                        print("TEXT:")
                        print(text)
                        print("HEX:")
                        print(hexed)
                        print("-" * 60)
        except KeyboardInterrupt:
                print("\nStopped by user")
        finally:
                sock.close()

def main():
        p = argparse.ArgumentParser(description="Simple UDP monitor")
        p.add_argument("--host", "-H", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
        p.add_argument("--port", "-p", type=int, default=9999, help="Port to listen on (default: 9999)")
        args = p.parse_args()
        try:
                run(args.host, args.port)
        except PermissionError:
                print("Permission denied: try a port > 1024 or run with privileges", file=sys.stderr)
                sys.exit(1)
        except Exception as e:
                print("Error:", e, file=sys.stderr)
                sys.exit(2)

if __name__ == "__main__":
        main()