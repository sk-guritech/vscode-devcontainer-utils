#!/usr/bin/env python3
import socket
import subprocess
import threading
import re
import sys
import signal
import argparse

def run_devcontainer_up(folder_path):
    try:
        print(f"Starting devcontainer for: {folder_path}")
        
        # Popenを使ってリアルタイムで出力を表示
        process = subprocess.Popen(
            ['devcontainer', 'up', '--workspace-folder', folder_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        output = []
        container_id = None
        
        # リアルタイムで出力を表示
        for line in iter(process.stdout.readline, ''):
            if line:
                line = line.rstrip()
                print(f"[devcontainer] {line}")
                output.append(line)
                
                # container idを抽出
                match = re.search(r'"containerId":"([a-f0-9]+)"', line)
                if match:
                    container_id = match.group(1)
                else:
                    # 別のパターンも試す
                    match = re.search(r'([a-f0-9]{12,})', line)
                    if match:
                        container_id = match.group(1)
        
        process.wait()
        
        if process.returncode != 0:
            print(f"devcontainer command failed with exit code: {process.returncode}")
            return f"error: devcontainer failed with exit code {process.returncode}"
        
        if container_id:
            print(f"Container ID found: {container_id}")
            return container_id
        else:
            full_output = '\n'.join(output)
            print("Warning: Container ID not found in output")
            return f"unknown: {full_output}"
            
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return f"error: {str(e)}"

def handle_client(conn, addr):
    try:
        data = conn.recv(1024).decode().strip()
        print(f"Received: {data} from {addr}")
        
        container_id = run_devcontainer_up(data)
        conn.send(container_id.encode())
        
    except Exception as e:
        try:
            conn.send(f"error: {str(e)}".encode())
        except:
            pass
    finally:
        try:
            conn.close()
        except:
            pass

def signal_handler(sig, frame):
    print("\nShutting down server...")
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description='DevContainer TCP Server')
    parser.add_argument('--port', type=int, default=9999, help='Port to listen on (default: 9999)')
    args = parser.parse_args()
    
    # Register signal handler for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Set timeout for accept() to allow checking for interrupts
    server.settimeout(1.0)
    
    server.bind(('0.0.0.0', args.port))
    server.listen(5)
    
    print(f"Server listening on port {args.port}")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            try:
                conn, addr = server.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                thread.daemon = True  # Make thread daemon so it doesn't block shutdown
                thread.start()
            except socket.timeout:
                continue  # Allow checking for interrupts
            except OSError:
                break  # Socket was closed
    except KeyboardInterrupt:
        pass
    finally:
        try:
            server.close()
        except:
            pass
        print("Server stopped.")
        sys.exit(0)

if __name__ == '__main__':
    main()
