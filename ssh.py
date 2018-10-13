import os
import paramiko
import aws

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

def connect_instance(instance, key_file):
    key = paramiko.RSAKey.from_private_key_file(key_file)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    instance_id = instance['InstanceId']
    ip_address = instance['PublicIpAddress']
    print("[connect] id: %s, ip address: %s" % (instance_id, ip_address))
    client.connect(ip_address, username='centos', pkey=key)
    return client

def get(client, remote_path, local_path):
    sftp = client.open_sftp()
    try:
        sftp.get(remote_path, local_path)
    except FileNotFoundError:
        print(remote_path + " is not found")
    except IOError as err:
        print(str(err))
    sftp.close()

def execute(instance, key_file, commands, out, err, sample, local_dir, remote_dir):
    client = connect_instance(instance, key_file)
    out_file = open(out, "w", 1024)
    err_file = open(err, "w")
    for command in commands:
        out_file.write("[command] start %s\n" % (command))
        stdin, stdout, stderr = client.exec_command(command)
        stdin.close()
        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                out_file.write(''.join(map(chr, \
                    stdout.channel.recv(len(stdout.channel.in_buffer)))))
        out_file.write("[command] %s done\n" % (command))
        exitcode = stdout.channel.recv_exit_status()
        for line in stdout:
            out_file.write(line)
        for line in stderr:
            err_file.write(line)
        if exitcode != 0:
            err_file.write("[error] exit code: %d\n" % (exitcode))
    out_file.close()
    err_file.close()

    local_path = os.path.join(local_dir, sample)
    remote_path = os.path.join(remote_dir, sample)
    get(client, remote_path, local_path)
    client.close()
    aws.terminate_instances([instance['InstanceId']])
