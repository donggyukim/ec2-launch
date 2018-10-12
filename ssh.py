import threading
import os
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

def execute_commands(names, clients, commands, _dir=None):
    assert len(clients) == len(names)
    assert len(clients) == len(commands)
    target_dir = _dir if _dir is not None else ""

    class ExecutionThread(threading.Thread):
        def __init__(self, name, client, command):
            super(ExecutionThread, self).__init__()
            self.name = name
            self.client = client
            self.command = command
            self.out = open(os.path.join(target_dir, name + ".out"), "a")
            self.err = open(os.path.join(target_dir, name + ".err"), "a")

        def run(self):
            self.out.write("[command] start %s\n" % (self.command))
            _, stdout, stderr = self.client.exec_command(self.command)
            while not stdout.channel.exit_status_ready() or stdout.channel.recv_ready():
                if stdout.channel.recv_ready():
                    self.out.write(''.join(map(chr, \
                        stdout.channel.recv(len(stdout.channel.in_buffer)))))
            self.out.write("[command] %s done\n" % (self.command))
            exitcode = stdout.channel.recv_exit_status()
            for line in stderr:
                self.err.write(line)
            if exitcode != 0:
                self.err.write("[error] exit code: %d\n" % (exitcode))
            self.out.close()
            self.err.close()

    threads = []
    for name, client, command in zip(names, clients, commands):
        thread = ExecutionThread(name, client, command)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

def get(client, remote_path, local_path):
    sftp = client.open_sftp()
    try:
        sftp.get(remote_path, local_path)
    except FileNotFoundError:
        print(remote_path + " is not found")
    except IOError as err:
        print(str(err))
    sftp.close()

def close(clients):
    for client in clients:
        client.close()
