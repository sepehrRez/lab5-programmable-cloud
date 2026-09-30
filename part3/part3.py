#!/usr/bin/env python3

import os
from google.cloud import compute_v1
import google.oauth2.service_account as service_account

# Configuration variables
PROJECT = 'crucial-media-506802-a8'
ZONE = 'us-central1-a'

HERE = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(HERE, 'service-credentials.json')

# Authenticate using the downloaded Service Account key JSON file
credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
instances_client = compute_v1.InstancesClient(credentials=credentials)

# Startup script for VM-1:
# Fetches credentials and part1 code from instance metadata, sets environment variables, and launches VM-2
VM1_STARTUP = """#!/bin/bash
apt-get update
apt-get install -y python3 python3-pip
mkdir -p /srv && cd /srv

MD=http://metadata.google.internal/computeMetadata/v1/instance/attributes
curl -s $MD/service-credentials -H "Metadata-Flavor: Google" > service-credentials.json
curl -s $MD/vm1-launch-vm2-code -H "Metadata-Flavor: Google" > vm1-launch-vm2-code.py

export GOOGLE_CLOUD_PROJECT=$(curl -s $MD/project -H "Metadata-Flavor: Google")
export GOOGLE_APPLICATION_CREDENTIALS=/srv/service-credentials.json

pip3 install google-cloud-compute
python3 vm1-launch-vm2-code.py
"""

def create_vm1():
    # Read part1.py code to embed in metadata
    part1_code_path = os.path.join(HERE, '..', 'part1', 'part1.py')
    with open(part1_code_path, 'r') as f:
        launch_code = f.read()

    # Read service account JSON contents to embed in metadata
    with open(CREDENTIALS_PATH, 'r') as f:
        key_json = f.read()

    def make_item(k, v):
        return compute_v1.Items(key=k, value=v)

    # Configure boot disk for VM-1
    disk = compute_v1.AttachedDisk(
        auto_delete=True,
        boot=True,
        initialize_params=compute_v1.AttachedDiskInitializeParams(
            source_image='projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts'
        ),
    )

    # Configure network interface
    nic = compute_v1.NetworkInterface(
        network='global/networks/default',
        access_configs=[compute_v1.AccessConfig(name='External NAT', type_='ONE_TO_ONE_NAT')],
    )

    # Configure VM-1 instance resource and attach required metadata items
    instance = compute_v1.Instance(
        name='vm-1',
        machine_type=f'zones/{ZONE}/machineTypes/e2-medium', # یا f1-micro
        disks=[disk],
        network_interfaces=[nic],
        metadata=compute_v1.Metadata(items=[
            make_item('startup-script', VM1_STARTUP),
            make_item('service-credentials', key_json),
            make_item('vm1-launch-vm2-code', launch_code),
            make_item('project', PROJECT),
        ]),
    )

    print("Creating vm-1...")
    op = instances_client.insert(project=PROJECT, zone=ZONE, instance_resource=instance)
    op.result()
    print('vm-1 created successfully!')
    print('vm-1 is now installing dependencies and will launch VM-2 shortly.')

if __name__ == '__main__':
    create_vm1()
