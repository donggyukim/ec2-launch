#!/usr/bin/env python3

import argparse
import os
from thread import ExecutionThread
import yaml
import aws
import ssh

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-k", "--key", dest="key", type=str, required=True,
        help="key file")
    parser.add_argument(
        "-w", "--workload", dest="workload", type=str, required=True,
        help="workload yaml file")
    parser.add_argument(
        "-d", "--design", dest="design", type=str, required=True,
        help="design yaml file")

    args = parser.parse_args()

    # Load setup

    with open("configs/common.yml", "r") as _f:
        data = yaml.load(_f)
        ami = data["ami"]
        root_dir = data["root_dir"]

    with open(args.design) as _f:
        data = yaml.load(_f)
        project = data["project"]
        design = data["design"]
        config = data["config"]
        agfi = data["agfi"]

    full_config = project + "." + config
    driver_dir = os.path.join(root_dir, "output", "f1", project + "." + config)

    with open(args.workload) as _f:
        data = yaml.load(_f)
        bin_dir = data["bin_dir"]
        benchmarks = data["benchmarks"]

    # Launch instances
    count = len(benchmarks)
    instances = aws.launch_instances(ami, count=count)
    aws.wait_on_instance_launches(instances)
    instance_ids = [instance.id for instance in instances]
    instance_descs = aws.describe_instances(instance_ids)

    # SSH to instances
    clients = ssh.connect_instances(instance_descs, args.key)

    # Set stdout/stderr file for each benchmark
    command_sets = []
    outs = []
    errs = []
    samples = []

    if not os.path.exists(full_config):
        os.makedirs(full_config)

    for benchmark in benchmarks:
        outs.append(os.path.join(full_config, benchmark + ".out"))
        errs.append(os.path.join(full_config, benchmark + ".err"))
        samples.append(benchmarks[benchmark]["sample"])
        commands = []
        commands.append("cd %s && ./bin/load-afi.sh %s" % (root_dir, agfi))
        commands.append(
            "source /home/centos/.bash_profile && " \
            "make -C %s run PROJECT=%s DESIGN=%s " \
            "CONFIG_PROJECT=%s CONFIG=%s SIM_BINARY=%s/%s" % (
                root_dir, project, design, project, config, bin_dir,
                benchmarks[benchmark]["binary"]))
        command_sets.append(commands)


    # Start threading
    threads = []
    for client, instance, commands, out, err, sample \
        in zip(clients, instances, command_sets, outs, errs, samples):
        thread = ExecutionThread(
            client, instance, commands, out, err, sample, full_config, driver_dir)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()
