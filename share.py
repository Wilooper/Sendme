import os
import sys
import http.server
import socketserver
import threading
import subprocess
import time
import signal
import re
import argparse

class FileSharingHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, file_path=None, **kwargs):
        self.file_path = file_path
        if file_path:
            self.directory = os.path.dirname(file_path)
            self.filename = os.path.basename(file_path)
        else:
            self.directory = os.getcwd()
        super().__init__(*args, directory=self.directory, **kwargs)

    def do_GET(self):
        if self.file_path:
            # Normalize the path
            if self.path == '/' or self.path == '/'+self.filename:
                self.path = self.filename
                return super().do_GET()
            else:
                self.send_error(404, "Not Found")
        else:
            super().do_GET()

def check_cloudflared():
    """Check if cloudflared is available in PATH."""
    try:
        subprocess.run(['cloudflared', '--version'], 
                       stdout=subprocess.DEVNULL, 
                       stderr=subprocess.DEVNULL,
                       check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_local_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def main():
    parser = argparse.ArgumentParser(description='Share files or directories via a temporary tunnel.')
    parser.add_argument('path', nargs='?', default='.', help='File or directory to share (default: current directory)')
    parser.add_argument('--timeout', type=int, help='Timeout in seconds after which the sharing will stop')
    args = parser.parse_args()

    share_path = os.path.abspath(args.path)
    if not os.path.exists(share_path):
        print(f"Error: Path '{share_path}' does not exist.")
        sys.exit(1)

    if not check_cloudflared():
        print("Error: cloudflared not found in PATH. Please install cloudflared first.")
        print("You can install it with: pkg install cloudflared (in Termux) or follow instructions at https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation")
        sys.exit(1)

    is_file = os.path.isfile(share_path)
    if is_file:
        print(f"Sharing file: {share_path}")
    else:
        print(f"Sharing directory: {share_path}")

    # Create handler class with the file_path if sharing a file
    if is_file:
        handler_class = lambda *args: FileSharingHandler(*args, file_path=share_path)
    else:
        handler_class = FileSharingHandler

    # Start server on a random port
    port = 0  # Let OS choose a free port
    server = socketserver.TCPServer(("", port), handler_class)
    port = server.server_address[1]  # Get the actual port assigned
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    local_ip = get_local_ip()
    print(f"Local server started on http://{local_ip}:{port}")

    # Start cloudflared tunnel
    print("Starting cloudflared tunnel...")
    cloudflared_cmd = [
        'cloudflared',
        'tunnel',
        '--url',
        f'http://localhost:{port}',
        '--no-autoupdate'
    ]
    
    try:
        cloudflared_process = subprocess.Popen(
            cloudflared_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        tunnel_url = None
        # Read output to find the tunnel URL
        while True:
            line = cloudflared_process.stdout.readline()
            if not line:
                break
            print(line, end='')  # Print cloudflared output live
            # Look for URL patterns in the output - try to find a trycloudflare.com URL
            url_match = re.search(r'https?://[a-zA-Z0-9\-]+\.trycloudflare\.com[^\s\)]*', line)
            if url_match:
                tunnel_url = url_match.group(0)
                # Clean up any trailing brackets or punctuation
                tunnel_url = re.sub(r'[\]\),.!?;]+$', '', tunnel_url)
                break
        
        if tunnel_url:
            print(f"\n* * * Tunnel URL: {tunnel_url} * * *")
            print("Share this URL to allow others to download the file(s)")
        else:
            print("\n* * * Tunnel established but URL not detected in output * * *")
            print("Check the cloudflared output above for the URL")
        
        # Set up timeout if specified
        if args.timeout is not None:
            print(f"* * * Will automatically shut down after {args.timeout} seconds * * *")
            time.sleep(args.timeout)
            print("\n* * * Timeout reached, shutting down... * * *")
            raise KeyboardInterrupt  # Trigger shutdown
        
        # Wait for cloudflared process to finish or user interrupt
        cloudflared_process.wait()
        
    except KeyboardInterrupt:
        print("\n* * * Shutting down... * * *")
    except Exception as e:
        print(f"\nError with cloudflared: {e}")
    finally:
        print("Shutting down server...")
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1)
        if 'cloudflared_process' in locals() and cloudflared_process.poll() is None:
            cloudflared_process.terminate()
            cloudflared_process.wait()
        print("Done.")

if __name__ == '__main__':
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    main()