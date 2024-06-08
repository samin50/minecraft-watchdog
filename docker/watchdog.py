# pylint: disable=missing-module-docstring, broad-exception-caught, invalid-name, line-too-long, import-error, no-member, bare-except
# pylance: reportGeneralTypeIssues=false
import os
import sys
import time
import boto3
import requests
from requests.packages import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if len(sys.argv) > 1:
    try:
        print("Testing watchdog")
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except:
        print("Failed to load .env file")

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
    Check if any server is running
    """
    res = []
    try:
        res = [session.get(f'https://{SERVERNAME}:{CRAFTYPORT}/api/v2/servers/{id}/stats', verify=False).json()["data"]["running"] for id in server_ids]
    except:
        pass
    return any(res)

def players_on(server_ids):
    """
    Check if the server is running
    """
    res = []
    try:
        res = [session.get(f'https://{SERVERNAME}:{CRAFTYPORT}/api/v2/servers/{id}/stats', verify=False).json()["data"]["online"] for id in server_ids]
    except:
        pass
    return any(res)

CLUSTER = get_req_var('CLUSTER')
SERVICE = get_req_var('SERVICE')
TOKEN = get_req_var('TOKEN')

SERVERNAME = os.environ.get('SERVERNAME', 'localhost')
CRAFTYPORT = int(os.environ.get('CRAFTYPORT', "8443"))
STARTUPMIN = int(os.environ.get('STARTUPMIN', "10"))
SHUTDOWNMIN = int(os.environ.get('SHUTDOWNMIN', "10"))

HEADERS = {
    "Authorization": TOKEN
}

VERSION = os.environ.get('VERSION', 'Unknown')

session = requests.Session()
session.headers.update(HEADERS)

print(f"Watchdog version: {VERSION}")
print(f"Waiting at least {STARTUPMIN} minutes for Crafty to start")
connected = False
startTime = time.time()
# Check if Crafty is up
while time.time() - startTime < STARTUPMIN * 60:
    try:
        # Check if Crafty is up
        if not connected and session.get(f'https://{SERVERNAME}:{CRAFTYPORT}/api/v2', verify=False).status_code == 200:
            print("Crafty is up")
            connected = True
        # Get all server ids but only if connected
        if connected:
            SERVER_IDS = [server["server_id"] for server in session.get(f'https://{SERVERNAME}:{CRAFTYPORT}/api/v2/servers', verify=False).json()["data"]]
            break
    except:
        pass
    time.sleep(1)
if not connected:
    print("Crafty did not start in time")
    update_ecs_service(CLUSTER, SERVICE, 0)
    sys.exit(1)

print(f"Crafty took {time.time() - startTime} seconds to start")
# Grab all crafty servers
print("Servers:", SERVER_IDS)

# Check if any servers running
connected = False
startTime = time.time()
while not connected:
    connected = server_running(SERVER_IDS)
    if connected:
        print("Servers are running.")
        break
    # Wait for 60 seconds
    for _ in range(60):
        time.sleep(1)
    # Time to shutdown
    if time.time() - startTime > SHUTDOWNMIN * 60:
        print("No servers running, terminating.")
        update_ecs_service(CLUSTER, SERVICE, 0)
        sys.exit(1)

# Shutdown watcher
print(f"Waiting for at least {SHUTDOWNMIN} minutes of server inactivity.")
startTime = time.time()
while time.time() - startTime < SHUTDOWNMIN * 60:
    playersOn = players_on(SERVER_IDS)
    if not playersOn:
        print("No players online.")
    else:
        print("Players online, resetting timer.")
        startTime = time.time()
    # Wait for 20 seconds
    for _ in range(20):
        time.sleep(1)
# Time to shutdown
if time.time() - startTime > SHUTDOWNMIN * 60:
    print("No players online. Terminating.")
    update_ecs_service(CLUSTER, SERVICE, 0)
    sys.exit(1)
