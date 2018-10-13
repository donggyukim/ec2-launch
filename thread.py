import threading
import os
import aws
import ssh

class ExecutionThread(threading.Thread):
    def __init__(self, client, instance, commands, out, err, sample, local_dir, remote_dir):
        super(ExecutionThread, self).__init__()
        self.client = client
        self.instance = instance
        self.commands = commands
        self.out = out
        self.err = err
        self.local_path = os.path.join(local_dir, sample)
        self.remote_path = os.path.join(remote_dir, sample)

    def run(self):
        out_file = open(self.out, "w", 1024)
        err_file = open(self.err, "w")
        for command in self.commands:
            out_file.write("[command] start %s\n" % (command))
            _, stdout, stderr = self.client.exec_command(command)
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

        ssh.get(self.client, self.remote_path, self.local_path)
        self.client.close()
        aws.terminate_instances([self.instance])
