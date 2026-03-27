#!/usr/bin/env python3
import argparse
import os
import socket
import secrets
import string
import sys

import requests
from tqdm import tqdm

BUF = 4 * 1024 * 1024


def public_ip():
    return requests.get("https://api.ipify.org", timeout=5).text


def generate_token(n=6):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def parse_host_port(addr):
    """
    Parse 'host:port' into (host, port_int).
    For IPv6, use bracket form: '[::1]:9000'.
    """
    addr = addr.strip()
    if addr.startswith("["):
        host, _, rest = addr[1:].partition("]")
        if not rest.startswith(":"):
            raise ValueError(f"Invalid address: {addr}")
        return host, int(rest[1:])
    host, port_s = addr.rsplit(":", 1)
    return host, int(port_s)


def find_port(manual_port=None):
    if manual_port:
        return manual_port

    for p in range(70000, 70011):
        env = f"RUNPOD_TCP_PORT_{p}"
        ext = os.getenv(env)
        if not ext:
            continue
        port = int(ext)
        s = socket.socket()
        try:
            s.bind(("0.0.0.0", port))
            s.close()
            return port
        except OSError:
            s.close()
            continue

    print("No RunPod symmetric port available.")
    print("Re-run with: fastsend receive --port PORT OR fastsend send push --port PORT")
    sys.exit(1)


def collect_files(paths):
    """Expand paths into (relative_send_path, absolute_path) pairs."""
    files = []
    for p in paths:
        p = p.rstrip(os.sep)
        if os.path.isfile(p):
            files.append((os.path.basename(p), os.path.abspath(p)))
        elif os.path.isdir(p):
            base = os.path.dirname(p) or "."
            for root, _, filenames in os.walk(p):
                for fname in filenames:
                    abs_path = os.path.join(root, fname)
                    rel_path = os.path.relpath(abs_path, base)
                    files.append((rel_path, abs_path))
        else:
            print(f"Not found: {p}")
            sys.exit(1)
    return files


def recv_exact(conn, n):
    """Read exactly n bytes from socket."""
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed")
        buf += chunk
    return buf


# Shared sender logic (works for both direct send + push-mode server).
def send_files(conn, token, files):
    conn.sendall(token.encode().ljust(32))
    conn.sendall(str(len(files)).encode().ljust(8))

    for i, (rel_path, abs_path) in enumerate(files):
        size = os.path.getsize(abs_path)
        encoded_name = rel_path.encode()

        conn.sendall(str(len(encoded_name)).encode().ljust(8))
        conn.sendall(encoded_name)
        conn.sendall(str(size).encode().ljust(32))

        with open(abs_path, "rb") as f:
            pbar = tqdm(
                total=size,
                unit="B",
                unit_scale=True,
                desc=f"[{i+1}/{len(files)}] {rel_path}",
            )
            while True:
                chunk = f.read(BUF)
                if not chunk:
                    break
                conn.sendall(chunk)
                pbar.update(len(chunk))
            pbar.close()


# --------------- receive ---------------

def receive(port=None):
    port = find_port(port)
    token = generate_token()
    ip = public_ip()

    print()
    print(f"Listening on {ip}:{port}")
    print()
    print("Run this on the sender:")
    print()
    print(f"  fastsend send {ip}:{port} --token {token} FILE [FILE ...]")
    print()

    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", port))
    srv.listen(1)

    conn, addr = srv.accept()
    print(f"Connection from {addr[0]}")

    recv_token = recv_exact(conn, 32).decode().strip()
    if recv_token != token:
        print("Invalid token — rejected")
        conn.close()
        srv.close()
        return

    file_count = int(recv_exact(conn, 8).decode().strip())
    print(f"Receiving {file_count} file(s)\n")

    for i in range(file_count):
        name_len = int(recv_exact(conn, 8).decode().strip())
        name = recv_exact(conn, name_len).decode()
        size = int(recv_exact(conn, 32).decode().strip())

        parent = os.path.dirname(name)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(name, "wb") as f:
            pbar = tqdm(
                total=size, unit="B", unit_scale=True,
                desc=f"[{i+1}/{file_count}] {name}",
            )
            remaining = size
            while remaining > 0:
                chunk = conn.recv(min(BUF, remaining))
                if not chunk:
                    raise ConnectionError("Connection closed mid-transfer")
                f.write(chunk)
                pbar.update(len(chunk))
                remaining -= len(chunk)
            pbar.close()

    conn.close()
    srv.close()
    print("\nTransfer complete")


def receive_connect(connect_addr, token):
    host, port = parse_host_port(connect_addr)
    if not token:
        print("Token is required with --connect")
        sys.exit(1)

    s = socket.socket()
    s.connect((host, port))
    print(f"Connected to {host}:{port}")

    recv_token = recv_exact(s, 32).decode().strip()
    if recv_token != token:
        print("Invalid token — rejected")
        s.close()
        return

    file_count = int(recv_exact(s, 8).decode().strip())
    print(f"Receiving {file_count} file(s)\n")

    for i in range(file_count):
        name_len = int(recv_exact(s, 8).decode().strip())
        name = recv_exact(s, name_len).decode()
        size = int(recv_exact(s, 32).decode().strip())

        parent = os.path.dirname(name)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(name, "wb") as f:
            pbar = tqdm(
                total=size,
                unit="B",
                unit_scale=True,
                desc=f"[{i+1}/{file_count}] {name}",
            )
            remaining = size
            while remaining > 0:
                chunk = s.recv(min(BUF, remaining))
                if not chunk:
                    raise ConnectionError("Connection closed mid-transfer")
                f.write(chunk)
                pbar.update(len(chunk))
                remaining -= len(chunk)
            pbar.close()

    s.close()
    print("\nTransfer complete")


# --------------- send ---------------

def send(addr, token, paths):
    host, port = parse_host_port(addr)

    files = collect_files(paths)
    if not files:
        print("No files to send")
        sys.exit(1)

    total_size = sum(os.path.getsize(abs_p) for _, abs_p in files)
    print(f"Sending {len(files)} file(s)  ({total_size / 1024 / 1024:.1f} MB)\n")

    s = socket.socket()
    s.connect((host, port))
    send_files(s, token, files)

    s.close()
    print("\nTransfer complete")


def send_push(paths, port=None):
    """
    Push-mode:
    - Sender opens a TCP listener on a symmetric port (RunPod-friendly).
    - It prints a command for the receiver to connect outbound to that listener.
    """
    port = find_port(port)
    token = generate_token()
    ip = public_ip()

    files = collect_files(paths)
    if not files:
        print("No files to send")
        sys.exit(1)

    total_size = sum(os.path.getsize(abs_p) for _, abs_p in files)
    print()
    print(f"Listening on {ip}:{port}")
    print()
    print("Run this on the receiver:")
    print()
    print(f"  fastsend receive --connect {ip}:{port} --token {token}")
    print()

    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", port))
    srv.listen(1)

    conn, addr = srv.accept()
    print(f"Connection from {addr[0]}")

    send_files(conn, token, files)

    conn.close()
    srv.close()
    print("\nTransfer complete")


# --------------- CLI ---------------

def main():
    parser = argparse.ArgumentParser(
        prog="fastsend",
        description="Fast file transfer over direct TCP (RunPod-friendly)",
    )
    sub = parser.add_subparsers(dest="cmd")

    recv_p = sub.add_parser("receive", help="Listen for incoming files")
    recv_p.add_argument("--port", type=int, default=None, help="Manual port override")
    recv_p.add_argument(
        "--connect",
        type=str,
        default=None,
        help="Connect outbound to a push-mode sender as a client: host:port",
    )
    recv_p.add_argument("--token", type=str, default=None, help="Auth token (required with --connect)")

    send_p = sub.add_parser("send", help="Send files to a receiver")
    send_p.add_argument(
        "addr",
        help="Receiver address as host:port, or literal 'push' for push-mode",
    )
    send_p.add_argument("--token", required=False, help="Auth token from receiver (direct send mode)")
    send_p.add_argument("paths", nargs="+", help="Files or folders to send")
    send_p.add_argument("--port", type=int, default=None, help="Manual port override (push-mode)")

    args = parser.parse_args()

    if args.cmd == "receive":
        if args.connect:
            receive_connect(connect_addr=args.connect, token=args.token)
        else:
            receive(port=args.port)
    elif args.cmd == "send":
        if args.addr == "push":
            send_push(paths=args.paths, port=args.port)
        else:
            if not args.token:
                print("Direct send mode requires --token")
                sys.exit(1)
            send(args.addr, args.token, args.paths)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
