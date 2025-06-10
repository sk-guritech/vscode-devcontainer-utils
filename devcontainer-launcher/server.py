#!/usr/bin/env python3
import socket
import subprocess
import threading
import re
import sys
import argparse

def run_devcontainer_up(folder_path):
    try:
        result = subprocess.run(['devcontainer', 'up', '--workspace-folder', folder_path], 
                              capture_output=True, 
                              text=True, 
                              timeout=300,
                              shell=True,
                              encoding='utf-8',
                              errors='replace')
        
        # container idを抽出
        match = re.search(r'"containerId":"([a-f0-9]+)"', result.stdout)
        if match:
            return match.group(1)
        
        # 別のパターンも試す
        match = re.search(r'([a-f0-9]{12,})', result.stdout)
        if match:
            return match.group(1)
            
        return f"unknown: {result.stdout}"
    except Exception as e:
        return f"error: {str(e)}"

def handle_client(conn, addr):
    try:
        data = conn.recv(1024).decode().strip()
        print(f"Received: {data} from {addr}")
        
        container_id = run_devcontainer_up(data)
        conn.send(container_id.encode())
        
    except Exception as e:
        conn.send(f"error: {str(e)}".encode())
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description='DevContainer TCP Server')
    parser.add_argument('--port', type=int, default=9999, help='Port to listen on (default: 9999)')
    args = parser.parse_args()
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', args.port))
    server.listen(5)
    
    print(f"Server listening on port {args.port}")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.close()
        sys.exit(0)

if __name__ == '__main__':
    main()