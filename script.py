import time
import os
import requests
import json
import argparse
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

def handle_api_error(response, operation):
    try:
        error_detail = response.json()
        print(f"❌ Error occurred during {operation}:")
        print(f"Status code: {response.status_code}")
        print(f"Error details: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
    except:
        print(f"❌ Error occurred during {operation}:")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
    raise

def create_script_resource(script_path, script_name=None, description=""):
    # Load environment variables
    load_dotenv()

    # API credentials
    API_TOKEN = os.getenv('SAKURA_API_TOKEN')
    API_SECRET = os.getenv('SAKURA_API_SECRET')
    ZONE = os.getenv('SAKURA_ZONE', 'is1b')  # Default to is1b zone

    # Validate environment variables
    if not all([API_TOKEN, API_SECRET]):
        raise ValueError("Environment variables SAKURA_API_TOKEN and SAKURA_API_SECRET are not set.")

    # Check if script file exists
    if not os.path.exists(script_path):
        raise ValueError(f"Script file {script_path} not found.")

    # Read script file content
    with open(script_path, 'r') as f:
        script_content = f.read()
        


    # If script name is not specified, use filename
    if script_name is None:
        script_name = os.path.basename(script_path)

    # API configuration
    BASE_URL = f"https://secure.sakura.ad.jp/cloud/zone/{ZONE}/api/cloud/1.1"
    AUTH = HTTPBasicAuth(API_TOKEN, API_SECRET)

    # Create script resource
    print(f"Creating script '{script_name}'...")
    script_response = requests.post(
        f"{BASE_URL}/note",
        auth=AUTH,
        json={
            "Note": {
                "Name": script_name,
                "Class": "shell",
                "Content": script_content,
                "Description": description
            }
        }
    )

    if not script_response.ok:
        handle_api_error(script_response, "script creation")

    script_id = script_response.json()['Note']['ID']
    print(f"✅ Script '{script_name}' created successfully. ID: {script_id}")
    
    # Save results to JSON file
    with open('script_info.json', 'w') as f:
        json.dump({
            'script_id': script_id,
            'script_name': script_name,
            'zone': ZONE
        }, f)
        
    return script_id

def create_and_start():
    # Load environment variables
    load_dotenv()

    # API credentials
    API_TOKEN = os.getenv('SAKURA_API_TOKEN')
    API_SECRET = os.getenv('SAKURA_API_SECRET')
    ZONE = os.getenv('SAKURA_ZONE', 'is1b')  # Default to is1b zone
    SERVER_PASSWORD = os.getenv('SAKURA_SERVER_PASSWORD')
    SSH_KEY_ID = os.getenv('SAKURA_SSH_KEY_ID')

    # Validate environment variables
    if not all([API_TOKEN, API_SECRET]):
        raise ValueError("Environment variables SAKURA_API_TOKEN and SAKURA_API_SECRET are not set.")

    if not SERVER_PASSWORD:
        raise ValueError("Environment variable SAKURA_SERVER_PASSWORD is not set.")
    
    if not SSH_KEY_ID:
        raise ValueError("Environment variable SAKURA_SSH_KEY_ID is not set.")

    # Load script information (if script_info.json exists)
    script_id = None
    try:
        with open('script_info.json', 'r') as f:
            script_info = json.load(f)
            script_id = script_info.get('script_id')
            print(f"Loaded script ID: {script_id}")
    except FileNotFoundError:
        print("script_info.json not found. Creating server without startup script.")
    
    # API configuration
    BASE_URL = f"https://secure.sakura.ad.jp/cloud/zone/{ZONE}/api/cloud/1.1"
    AUTH = HTTPBasicAuth(API_TOKEN, API_SECRET)

    # Get disk configuration parameters from environment variables
    DISK_NAME = os.getenv('SAKURA_DISK_NAME', 'bz-ai-server-disk')
    DISK_SIZE_GB = int(os.getenv('SAKURA_DISK_SIZE_GB', '250'))
    SOURCE_ARCHIVE_ID = int(os.getenv('SAKURA_SOURCE_ARCHIVE_ID', '113600510456'))
    DISK_PLAN_ID = int(os.getenv('SAKURA_DISK_PLAN_ID', '4'))  # SSD plan
    
    # 1. Create disk (using specified archive)
    print("Creating disk...")
    disk_response = requests.post(
        f"{BASE_URL}/disk",
        auth=AUTH,
        json={
            "Disk": {
                "Name": DISK_NAME,
                "SizeMB": DISK_SIZE_GB * 1024,
                "SourceArchive": {"ID": SOURCE_ARCHIVE_ID},
                "Plan": {"ID": DISK_PLAN_ID}
            }
        }
    )
    if not disk_response.ok:
        handle_api_error(disk_response, "disk creation")
    disk_id = disk_response.json()['Disk']['ID']

 # Wait for disk to be ready (polling)
    print("Waiting for disk to be ready...")
    while True:
        status_response = requests.get(f"{BASE_URL}/disk/{disk_id}", auth=AUTH)
        if not status_response.ok:
            handle_api_error(status_response, "disk status check")
        status = status_response.json()
        if status['Disk']['Availability'] == 'available':
            break
        time.sleep(10)

    # Get hostname from environment variable
    HOST_NAME = os.getenv('SAKURA_HOST_NAME', 'bz-ai-1')
    
    # Update disk configuration
    print("Updating disk configuration...")
    config_data = {
        "Password": SERVER_PASSWORD,
        "DisablePWAuth": True,
        "HostName": HOST_NAME,
        "SSHKeys": [{"ID": int(SSH_KEY_ID)}]
    }
    
    # Add script ID if it exists
    if script_id:
        config_data["Notes"] = {"ID": script_id}
    
    config_response = requests.put(
        f"{BASE_URL}/disk/{disk_id}/config",
        auth=AUTH,
        json=config_data
    )
    if not config_response.ok:
        handle_api_error(config_response, "disk configuration update")

    # Wait for disk to be ready again after configuration update
    print("Waiting for disk to be ready after configuration update...")
    while True:
        status_response = requests.get(f"{BASE_URL}/disk/{disk_id}", auth=AUTH)
        if not status_response.ok:
            handle_api_error(status_response, "disk status check")
        status = status_response.json()
        if status['Disk']['Availability'] == 'available':
            break
        time.sleep(10)

    # Get server configuration parameters from environment variables
    SERVER_NAME = os.getenv('SAKURA_SERVER_NAME', 'bz-ai-server')
    SERVER_CPU = int(os.getenv('SAKURA_SERVER_CPU', '24'))
    SERVER_GPU = int(os.getenv('SAKURA_SERVER_GPU', '1'))
    SERVER_GPU_MODEL = os.getenv('SAKURA_SERVER_GPU_MODEL', 'nvidia_h100_80gbvram')
    SERVER_MEMORY_MB = int(os.getenv('SAKURA_SERVER_MEMORY_MB', '245760'))
    
    # 2. Create server
    print("Creating server...")
    server_data = {
        "Server": {
            "Name": SERVER_NAME,
            "ServerPlan": {
                # "ID": 110480129,  # High-performance VRT plan
                # "Commitment": "none",
                "CPU": SERVER_CPU,
                "GPU": SERVER_GPU,
                "GPUModel": SERVER_GPU_MODEL,
                "MemoryMB": SERVER_MEMORY_MB,
            },
            "ConnectedSwitches": [{"Scope": "shared"}],
            "InterfaceDriver": "virtio"
        }
    }
    
    # Add startup script if script ID exists
    if script_id:
        server_data["Server"]["StartupScripts"] = [{"ID": script_id}]
    
    server_response = requests.post(
        f"{BASE_URL}/server",
        auth=AUTH,
        json=server_data
    )
    if not server_response.ok:
        handle_api_error(server_response, "server creation")
    server_id = server_response.json()['Server']['ID']

    # 3. Attach disk to server
    print("Attaching disk to server...")
    attach_response = requests.put(
        f"{BASE_URL}/disk/{disk_id}/to/server/{server_id}",
        auth=AUTH
    )
    if not attach_response.ok:
        handle_api_error(attach_response, "disk attachment")


    # 4. Start server
    print("Starting server...")
    power_on_response = requests.put(
        f"{BASE_URL}/server/{server_id}/power",
        auth=AUTH
    )
    if not power_on_response.ok:
        handle_api_error(power_on_response, "server startup")

    # Wait for startup (optional)
    time.sleep(60)  # Wait for startup if needed

    # Get server details to obtain IP address
    print("Getting server details...")
    server_details_response = requests.get(
        f"{BASE_URL}/server/{server_id}",
        auth=AUTH
    )
    if not server_details_response.ok:
        handle_api_error(server_details_response, "server details retrieval")
    
    server_details = server_details_response.json()
    
    # Extract IP address from interfaces
    ip_address = None
    if 'Interfaces' in server_details['Server'] and server_details['Server']['Interfaces']:
        for interface in server_details['Server']['Interfaces']:
            if 'IPAddress' in interface and interface['IPAddress']:
                ip_address = interface['IPAddress']
                break
    
    # Save IDs to file for later use
    with open('server_info.json', 'w') as f:
        json.dump({
            'server_id': server_id,
            'disk_id': disk_id,
            'ip_address': ip_address,
            'zone': ZONE
        }, f)

    print("✅ Server creation and startup completed successfully.")
    if ip_address:
        print(f"🌐 Server IP address: {ip_address}")
        print(f"📝 You can connect to the server using: ssh root@{ip_address}")
    else:
        print("⚠️ Could not retrieve server IP address. Please check the Sakura Cloud console.")

def shutdown_and_cleanup():
    # Load environment variables
    load_dotenv()

    # API credentials
    API_TOKEN = os.getenv('SAKURA_API_TOKEN')
    API_SECRET = os.getenv('SAKURA_API_SECRET')

    # Load server information
    try:
        with open('server_info.json', 'r') as f:
            info = json.load(f)
            server_id = info['server_id']
            disk_id = info['disk_id']
            ZONE = info['zone']
    except FileNotFoundError:
        print("❌ server_info.json not found. Please run create_and_start first.")
        return

    # API configuration
    BASE_URL = f"https://secure.sakura.ad.jp/cloud/zone/{ZONE}/api/cloud/1.1"
    AUTH = HTTPBasicAuth(API_TOKEN, API_SECRET)

    # 5. Stop server
    print("Stopping server...")
    power_off_response = requests.delete(
        f"{BASE_URL}/server/{server_id}/power",
        auth=AUTH
    )
    print(power_off_response.text)

    if not power_off_response.ok:
        handle_api_error(power_off_response, "server shutdown")

    # Wait for shutdown (optional)
    while True:
        status_response = requests.get(f"{BASE_URL}/server/{server_id}", auth=AUTH)
        print(status_response.text)
        if not status_response.ok:
            handle_api_error(status_response, "server status check")
        status = status_response.json()
        if status['Server']['Instance']['Status'] == 'down':
            break
        time.sleep(10)

    # 6. Delete server
    print("Deleting server...")
    delete_server_response = requests.delete(
        f"{BASE_URL}/server/{server_id}",
        auth=AUTH
    )
    if not delete_server_response.ok:
        handle_api_error(delete_server_response, "server deletion")

    # 7. Delete disk
    print("Deleting disk...")
    delete_disk_response = requests.delete(
        f"{BASE_URL}/disk/{disk_id}",
        auth=AUTH
    )
    if not delete_disk_response.ok:
        handle_api_error(delete_disk_response, "disk deletion")

    # Remove server info file
    os.remove('server_info.json')

    print("✅ Server shutdown and cleanup completed successfully.")

def main():
    parser = argparse.ArgumentParser(description='Sakura Cloud Server Management')
    subparsers = parser.add_subparsers(dest='action', help='Action to perform')
    
    # サーバー起動・停止コマンド
    server_parser = subparsers.add_parser('server', help='Server management')
    server_parser.add_argument('operation', choices=['start', 'stop'], help='Operation to perform on server')
    
    # スクリプト作成コマンド
    script_parser = subparsers.add_parser('create-script', help='Create script resource')
    script_parser.add_argument('script_path', help='Path to the script file')
    script_parser.add_argument('--name', help='Name of the script resource (defaults to filename)')
    script_parser.add_argument('--description', default="", help='Description of the script')
    
    args = parser.parse_args()
    
    if args.action == 'server':
        if args.operation == 'start':
            create_and_start()
        elif args.operation == 'stop':
            shutdown_and_cleanup()
    elif args.action == 'create-script':
        create_script_resource(args.script_path, args.name, args.description)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
