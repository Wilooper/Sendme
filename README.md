# Simple File Sharing Tool

A lightweight tool to share files or directories via a temporary tunnel using Cloudflare Tunnel.

## Requirements

- Python 3.x
- cloudflared (install with: `pkg install cloudflared` in Termux or follow instructions at https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation)

## Usage

```bash
python3 share.py [file_or_directory] [--timeout SECONDS]
```

If no path is specified, the current directory will be shared.

## Features

- Share individual files or entire directories
- Automatic timeout functionality with `--timeout` option
- Uses Cloudflare Tunnel for reliable, secure connections
- No authentication required for temporary tunnels
- Works in Termux/Ubuntu environment

## Examples

```bash
# Share a single file
python3 share.py document.pdf

# Share a directory
python3 share.py ./photos

# Share current directory
python3 share.py

# Share with automatic timeout after 60 seconds
python3 share.py document.pdf --timeout 60
```

## How it works

1. Starts a local HTTP server to serve the specified file or directory
2. Creates a Cloudflare Tunnel to expose the local server to the internet
3. Provides a public trycloudflare.com URL that others can use to download the file(s)
4. The tunnel remains active until you stop the program (Ctrl+C) or timeout is reached

## Notes

- The tool uses Cloudflare's quick tunnel feature, which doesn't require an account
- For large files, transfer speed depends on your internet connection
- The tunnel is temporary and dies when you stop the program or timeout is reached
- Anyone with the URL can access your file, so use discretion with sensitive data
- To install cloudflared in Termux: `pkg install cloudflared`

## Files in this project

- `share.py`: The main file sharing script
- `test.txt`: A sample file used for testing
- `README.md`: This file