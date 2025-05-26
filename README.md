# Sakura Cloud API

Scripts for creating, starting, and stopping servers using the Sakura Cloud API.

## Setup

1. Create a `.env` file in the project's root directory and set the following environment variables:

```
# Sakura Cloud API Authentication
SAKURA_API_TOKEN=your_api_token_here
SAKURA_API_SECRET=your_api_secret_here
SAKURA_ZONE=is1b

# Server Settings
SAKURA_SERVER_PASSWORD=your_server_password_here
SAKURA_SSH_KEY_ID=your_ssh_key_id_here
SAKURA_HOST_NAME=bz-ai-1
SAKURA_SERVER_NAME=bz-ai-server
SAKURA_SERVER_CPU=24
SAKURA_SERVER_GPU=1
SAKURA_SERVER_GPU_MODEL=nvidia_h100_80gbvram
SAKURA_SERVER_MEMORY_MB=245760

# Disk Settings
SAKURA_DISK_NAME=bz-ai-server-disk
SAKURA_DISK_SIZE_GB=250
SAKURA_SOURCE_ARCHIVE_ID=113600510456
SAKURA_DISK_PLAN_ID=4
```

2. Install the required Python packages:

```bash
pip install requests python-dotenv
```

## Usage

### Creating Script Resources

```bash
python script.py create-script path/to/your/script.sh --name "My Startup Script" --description "Description"
```

### Creating and Starting a Server

```bash
python script.py server start
```

### Stopping and Deleting a Server

```bash
python script.py server stop
```

## Notes

- Manage environment variables in the `.env` file and do not include sensitive information (passwords, API keys, etc.) directly in the source code.
- Add the `.env` file to `.gitignore` to avoid committing it to Git.

## Features

- Create and configure servers with GPU support
- Manage disk creation and attachment
- Handle server startup and shutdown
- Configure SSH keys and startup scripts
- Upload shell scripts to Sakura Cloud as script resources

## Prerequisites

- Python 3.x
- Required Python packages:
  - requests
  - python-dotenv

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd sakura-cloud-api
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your Sakura Cloud credentials:
```
SAKURA_API_TOKEN=your_api_token
SAKURA_API_SECRET=your_api_secret
SAKURA_ZONE=is1b  # Optional, defaults to is1b
```

## Usage

### Creating Script Resources

Before creating a server, you can upload a shell script to Sakura Cloud as a script resource. This script can be used as a startup script when a server boots:

```bash
# Upload a script with default name (filename)
python script.py create-script path/to/your_script.sh

# Upload a script with custom name and description
python script.py create-script path/to/your_script.sh --name "Custom Script Name" --description "Script description"
```

When you create a script resource, its ID is saved to `script_info.json`. This ID will be automatically used when you start a new server.

### Server Management

Start a server:
```bash
python script.py server start
```

Stop and clean up a server:
```bash
python script.py server stop
```

## How Script Resources Work

1. When you run the `create-script` command, the script is uploaded to Sakura Cloud and registered as a script resource.
2. The script ID is saved to `script_info.json`.
3. When you start a server using `server start`, the script will be:
   - Attached to the disk configuration as a Note
   - Added to the server as a StartupScript
4. The script automatically runs when the server boots.

## Configuration

The script uses the following configuration:

- Server Plan: High-performance VRT with NVIDIA H100 GPU
- Disk Size: 250GB SSD
- SSH Key: Configured via disk settings
- Startup Script: Loaded from `script_info.json` if available

## License

MIT License