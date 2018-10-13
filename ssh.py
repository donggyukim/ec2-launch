import paramiko

def connect_instances(instances, key_file):
    key = paramiko.RSAKey.from_private_key_file(key_file)
    clients = list()
    for instance in instances:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        instance_id = instance['InstanceId']
        ip_address = instance['PublicIpAddress']
        print("[connect] id: %s, ip address: %s" % (instance_id, ip_address))
        client.connect(ip_address, username='centos', pkey=key)
        clients.append(client)

    return clients

def get(client, remote_path, local_path):
    sftp = client.open_sftp()
    try:
        sftp.get(remote_path, local_path)
    except FileNotFoundError:
        print(remote_path + " is not found")
    except IOError as err:
        print(str(err))
    sftp.close()
