#!/usr/bin/env python3
import socket
import subprocess
import threading
import re
import sys
import signal
import argparse
import os
import platform

def find_devcontainer_command():
    """Find the devcontainer command based on platform"""
    if platform.system() == 'Windows':
        # First, check if devcontainer CLI is directly available
        try:
            result = subprocess.run(['where', 'devcontainer'], capture_output=True, text=True)
            if result.returncode == 0:
                devcontainer_path = result.stdout.strip().split('\n')[0]
                if devcontainer_path:
                    return [devcontainer_path]
        except:
            pass
        
        # Check common devcontainer CLI locations on Windows
        possible_devcontainer_paths = []
        
        # Try to get npm prefix
        try:
            npm_prefix = subprocess.run(['npm', 'prefix', '-g'], capture_output=True, text=True).stdout.strip()
            if npm_prefix:
                possible_devcontainer_paths.extend([
                    os.path.join(npm_prefix, 'node_modules', '.bin', 'devcontainer.cmd'),
                    os.path.join(npm_prefix, 'node_modules', '.bin', 'devcontainer'),
                ])
        except:
            pass
        
        # Add default npm locations
        possible_devcontainer_paths.extend([
            os.path.join(os.environ.get('APPDATA', ''), 'npm', 'devcontainer.cmd'),
            os.path.join(os.environ.get('APPDATA', ''), 'npm', 'devcontainer'),
        ])
        
        for path in possible_devcontainer_paths:
            if os.path.exists(path):
                return [path]
        
        # If not found, try direct devcontainer command (might be in PATH)
        return ['devcontainer']
    else:
        # On Unix-like systems, use devcontainer directly
        return ['devcontainer']

def run_devcontainer_up(folder_path):
    try:
        print(f"Starting devcontainer for: {folder_path}")
        
        # Get the appropriate command
        devcontainer_cmd = find_devcontainer_command()
        cmd = devcontainer_cmd + ['up', '--workspace-folder', folder_path]
        
        # Add SSH key mount if github key exists
        ssh_key_path = os.path.expanduser('~/.ssh/github')
        if os.path.exists(ssh_key_path):
            cmd.extend(['--mount', f'type=bind,source={ssh_key_path},target=/home/vscode/.ssh/id_rsa'])
            print(f"Adding SSH key mount to /home/vscode/.ssh/id_rsa: {ssh_key_path}")
        
        # Add .gitconfig mount if exists
        gitconfig_path = os.path.expanduser('~/.gitconfig')
        if os.path.exists(gitconfig_path):
            cmd.extend(['--mount', f'type=bind,source={gitconfig_path},target=/home/vscode/.gitconfig'])
            print(f"Adding .gitconfig mount to /home/vscode/.gitconfig: {gitconfig_path}")
        
        # Add GitHub CLI config mount if exists
        gh_config_path = os.path.expanduser('~/.config/gh')
        if os.path.exists(gh_config_path):
            cmd.extend(['--mount', f'type=bind,source={gh_config_path},target=/home/vscode/.config/gh'])
            print(f"Adding GitHub CLI config mount to /home/vscode/.config/gh: {gh_config_path}")
        
        print(f"Running command: {' '.join(cmd)}")
        
        # Popenを使ってリアルタイムで出力を表示
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            shell=(platform.system() == 'Windows')  # Use shell on Windows
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
            
            # Fix permissions for mounted directories and add known_hosts
            print("Fixing permissions for mounted directories and setting up known_hosts...")
            try:
                # First check if vscode user exists, then fix permissions
                subprocess.run([
                    'docker', 'exec', container_id, 
                    'bash', '-c', 
                    'if id vscode &>/dev/null; then mkdir -p /home/vscode/.ssh && chown -R vscode:vscode /home/vscode/.ssh; fi'
                ], capture_output=True)
                
                # Fix GitHub CLI config permissions
                subprocess.run([
                    'docker', 'exec', container_id,
                    'bash', '-c',
                    'if id vscode &>/dev/null && [ -d /home/vscode/.config/gh ]; then chown -R vscode:vscode /home/vscode/.config/gh; fi'
                ], capture_output=True)
                
                # Add GitHub to known_hosts as vscode user
                subprocess.run([
                    'docker', 'exec', container_id,
                    'su', '-', 'vscode', '-c',
                    'ssh-keyscan -H github.com >> ~/.ssh/known_hosts 2>/dev/null'
                ], capture_output=True)
                
                print("Permissions fixed and known_hosts updated successfully")
            except Exception as e:
                print(f"Warning: Failed to fix permissions: {e}")
            
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
