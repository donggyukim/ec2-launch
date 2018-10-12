import time
import boto3

KEYNAME = "Strober" # FIXME: parameterize?

def launch_instances(ami, instance_type="f1.2xlarge", count=1):
    ec2 = boto3.resource('ec2')
    instances = ec2.create_instances(
        ImageId=ami,
        InstanceType=instance_type,
        EbsOptimized=True,
        MinCount=count,
        MaxCount=count,
        KeyName=KEYNAME)

    return instances

def wait_on_instance_launches(instances):
    ec2 = boto3.client('ec2')
    print("Waiting for instance boots")
    for instance in instances:
        instance.wait_until_running()
    instance_ids = [instance.id for instance in instances]
    while True:
        statuses = ec2.describe_instance_status(InstanceIds=instance_ids)['InstanceStatuses']
        if all([status['InstanceStatus']['Status'] == 'ok' for status in statuses]):
            break
        time.sleep(1)
    print("all instances are booted!")

def describe_instances(instance_ids):
    ec2 = boto3.client('ec2')
    return ec2.describe_instances(InstanceIds=instance_ids)['Reservations'][0]['Instances']

def terminate_instances(instances):
    client = boto3.client('ec2')
    instance_ids = [instance.id for instance in instances]
    client.terminate_instances(InstanceIds=instance_ids)
    for instance_id in instance_ids:
        print(str(instance_id) + " terminated!")
