#!/usr/bin/env python3

import os
import time
import google.auth
from google.cloud import compute_v1

credentials, project = google.auth.default()

ZONE = 'us-central1-a'
INSTANCE_NAME = 'flask-vm'
MACHINE_TYPE = 'e2-micro'
TAG_NAME = 'allow-5000'

instances_client = compute_v1.InstancesClient(credentials=credentials)
firewalls_client = compute_v1.FirewallsClient(credentials=credentials)

# startup script to setup flask app on boot
STARTUP_SCRIPT = """#!/bin/bash
apt-get update
apt-get install -y python3 python3-pip git

cd /tmp
git clone https://github.com/cu-csci-4253-datacenter/flask-tutorial
cd flask-tutorial

python3 setup.py install
pip3 install -e .

export FLASK_APP=flaskr
flask init-db

nohup flask run -h 0.0.0.0 -p 5000 > /var/log/flask.log 2>&1 &
"""

def setup_firewall():
    # check if firewall rule already exists
    for rule in firewalls_client.list(project=project):
        if rule.name == TAG_NAME:
            print(f"Firewall '{TAG_NAME}' already exists.")
            return

    print("Creating firewall rule...")
    allowed_port = compute_v1.Allowed(I_p_protocol='tcp', ports=['5000'])
    firewall_rule = compute_v1.Firewall(
        name=TAG_NAME,
        direction='INGRESS',
        source_ranges=['0.0.0.0/0'],
        target_tags=[TAG_NAME],
        allowed=[allowed_port]
    )
    
    op = firewalls_client.insert(project=project, firewall_resource=firewall_rule)
    op.result()

def create_vm():
    print(f"Creating VM '{INSTANCE_NAME}'...")
    
    boot_disk = compute_v1.AttachedDisk(
        boot=True,
        auto_delete=True,
        initialize_params=compute_v1.AttachedDiskInitializeParams(
            source_image='projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts'
        )
    )

    network_interface = compute_v1.NetworkInterface(
        network='global/networks/default',
        access_configs=[compute_v1.AccessConfig(name='External NAT', type_='ONE_TO_ONE_NAT')]
    )

    instance_config = compute_v1.Instance(
        name=INSTANCE_NAME,
        machine_type=f"zones/{ZONE}/machineTypes/{MACHINE_TYPE}",
        disks=[boot_disk],
        network_interfaces=[network_interface],
        tags=compute_v1.Tags(items=[TAG_NAME]),
        metadata=compute_v1.Metadata(
            items=[compute_v1.Items(key='startup-script', value=STARTUP_SCRIPT)]
        )
    )

    op = instances_client.insert(project=project, zone=ZONE, instance_resource=instance_config)
    op.result()
    print("VM created successfully.")

def print_access_info():
    inst = instances_client.get(project=project, zone=ZONE, instance=INSTANCE_NAME)
    ip = inst.network_interfaces[0].access_configs[0].nat_i_p
    print(f"\nVM External IP: {ip}")
    print(f"Flask App URL: http://{ip}:5000")

def list_running_instances():
    print("\nRunning instances:")
    for inst in instances_client.list(project=project, zone=ZONE):
        print(f"- {inst.name}")

def main():
    print(f"Project: {project}")
    
    setup_firewall()
    create_vm()
    print_access_info()
    list_running_instances()

if __name__ == '__main__':
    main()
