# pylint: disable=missing-module-docstring, broad-exception-caught, invalid-name, line-too-long, import-error, no-member
# pylance: reportGeneralTypeIssues=false
import os
import sys
import time
import boto3
import requests
from requests.packages import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if len(sys.argv) > 1:
    print("Testing watchdog")
    from dotenv import load_dotenv
    load_dotenv()

def get_req_var(name):
    """
    Get required environment variable or exit
    """
    if name not in os.environ:
        print(f"Missing required environment variable: {name}")
        sys.exit(1)
    return os.environ[name]

def update_ecs_service(cluster_name, service_name, desired_count):
    """
    Update the ECS service with the desired count
    """
    # Create an ECS client
    ecs_client = boto3.client('ecs')
    # Update the ECS service
    try:
        response = ecs_client.update_service(
            cluster=cluster_name,
            service=service_name,
            desiredCount=desired_count
        )
        print("Update Service Response:", response)
    except Exception as e:
        print("Error updating ECS service:", str(e))

def server_running(server_ids):
    """
    Check if the server is running
    """
    return any(session.get(f'https://{SERVERADDRESS}:{CRAFTYPORT}/api/v2/servers/{id}/stats', timeout=10, verify=False).json()["data"]["running"] for id in server_ids)

def players_on(server_ids):
    """
    Check if the server is running
    """
    return any(session.get(f'https://{SERVERADDRESS}:{CRAFTYPORT}/api/v2/servers/{id}/stats', timeout=10, verify=False).json()["data"]["online"] for id in server_ids)

CLUSTER = get_req_var('CLUSTER')
SERVICE = get_req_var('SERVICE')
TOKEN = get_req_var('TOKEN')

CRAFTYPORT = os.environ.get('CRAFTYPORT', 8443)
SERVERADDRESS = os.environ.get('SERVERADDRESS', 'localhost')
STARTUPTIMEMIN = int(os.environ.get('STARTUPTIMEMIN', 10))
SHUTDOWNMIN = int(os.environ.get('SHUTDOWNMIN', 10))

HEADERS = {
    "Authorization": TOKEN
}

session = requests.Session()
session.headers.update(HEADERS)

print(f"Waiting at least {STARTUPTIMEMIN} minutes for Crafty to start")
counter = 0
# Check if Crafty is up
while counter < STARTUPTIMEMIN * 60:
    counter += 1
    if session.get(f'https://{SERVERADDRESS}:{CRAFTYPORT}/api/v2', timeout=10, verify=False).status_code == 200:
        print("Crafty is up")
        break
    time.sleep(1)
if counter == STARTUPTIMEMIN * 60:
    print("Crafty did not start in time")
    update_ecs_service(CLUSTER, SERVICE, 0)
    sys.exit(1)

# Grab all crafty servers
SERVER_IDS = [server["server_id"] for server in session.get(f'https://{SERVERADDRESS}:{CRAFTYPORT}/api/v2/servers', timeout=10, verify=False).json()["data"]]
print("Servers:", SERVER_IDS)

# Check if any servers running
connected = False
counter = 0
while not connected:
    connected = server_running(SERVER_IDS)
    if connected:
        print("Servers are running.")
        break
    # Wait for 60 seconds
    counter += 1
    for _ in range(60):
        time.sleep(1)
    # Time to shutdown
    if counter == STARTUPTIMEMIN:
        print("No servers running, terminating.")
        update_ecs_service(CLUSTER, SERVICE, 0)
        sys.exit(1)

# Shutdown watcher
counter = 0
while counter < SHUTDOWNMIN:
    playersOn = players_on(SERVER_IDS)
    if not playersOn:
        print("No players online.")
        counter += 1
        for _ in range(60):
            time.sleep(1)
    else:
        print("Players online, resetting counter.")
        counter = 0
        # Check every 20 seconds
        time.sleep(20)
# Time to shutdown
if counter == SHUTDOWNMIN:
    print("No players online. Terminating.")
    update_ecs_service(CLUSTER, SERVICE, 0)
    sys.exit(1)
