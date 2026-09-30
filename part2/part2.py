#!/usr/bin/env python3

import google.auth
from google.cloud import compute_v1

credentials, project = google.auth.default()

ZONE = 'us-central1-a'
SNAPSHOT_NAME = 'snapshot-1'
MACHINE_TYPE = 'e2-micro'
TAG_NAME = 'allow-5000'

instances_client = compute_v1.InstancesClient(credentials=credentials)

# Startup script to start the Flask app on boot from cloned disk
STARTUP_SCRIPT = """#!/bin/bash
cd /tmp/flask-tutorial
export FLASK_APP=flaskr
nohup flask run -h 0.0.0.0 -p 5000 > /var/log/flask.log 2>&1 &
"""

def create_clone(vm_name):
    # Configure boot disk from the manual snapshot
    boot_disk = compute_v1.AttachedDisk(
        boot=True,
        auto_delete=True,
        initialize_params=compute_v1.AttachedDiskInitializeParams(
            source_snapshot=f'projects/{project}/global/snapshots/{SNAPSHOT_NAME}'
        )
    )

    # Configure network interface
    network_interface = compute_v1.NetworkInterface(
        network='global/networks/default',
        access_configs=[compute_v1.AccessConfig(name='External NAT', type_='ONE_TO_ONE_NAT')]
    )

    # Assemble instance configuration
    instance_config = compute_v1.Instance(
        name=vm_name,
        machine_type=f"zones/{ZONE}/machineTypes/{MACHINE_TYPE}",
        disks=[boot_disk],
        network_interfaces=[network_interface],
        tags=compute_v1.Tags(items=[TAG_NAME]),
        metadata=compute_v1.Metadata(
            items=[compute_v1.Items(key='startup-script', value=STARTUP_SCRIPT)]
        )
    )

    # Submit creation request
    op = instances_client.insert(project=project, zone=ZONE, instance_resource=instance_config)
    op.result()

def main():
    print(f"Creating clones in project {project} using snapshot {SNAPSHOT_NAME}...")
    for i in range(1, 4):
        clone_name = f"gcelab2-clone-{i}"
        print(f"Creating {clone_name}...")
        create_clone(clone_name)
    print("All clones created successfully.")

if __name__ == '__main__':
    main()
