#!/usr/bin/env python3

import argparse
import os
import yaml
import aws
import ssh

SPEC_INT = [
    "400.perlbench",
]
"""
    "401.bzip2",
    "403.gcc",
    "429.mcf",
    "445.gobmk",
    "456.hmmer",
    "458.sjeng",
    "462.libquantum",
    "464.h264ref",
    "471.omnetpp",
    "473.astar",
    "483.xalancbmk"
]
"""

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

    # Set stdout/stderr file for each benchmark
    if not os.path.exists(full_config):
        os.makedirs(full_config)

    for benchmark in benchmarks:
        benchmark_data = benchmarks[benchmark]
        benchmark_data["stdout"] = os.path.join(full_config, benchmark + ".out")
        benchmark_data["stderr"] = os.path.join(full_config, benchmark + ".err")
        if os.path.exists(benchmark_data["stdout"]):
            os.remove(benchmark_data["stdout"])
        if os.path.exists(benchmark_data["stderr"]):
            os.remove(benchmark_data["stderr"])

    # Launch instances
    count = len(benchmarks)
    instances = aws.launch_instances(ami, count=count)
    aws.wait_on_instance_launches(instances)
    instance_ids = [instance.id for instance in instances]
    instance_descs = aws.describe_instances(instance_ids)

    # SSH to instances
    clients = ssh.connect_instances(instance_descs, args.key)

    load_afi = [
        "cd %s && ./bin/load-afi.sh %s" % (root_dir, agfi)
        for _ in range(count)
    ]
    ssh.execute_commands(clients, benchmarks, load_afi)

    # Run simulations
    run_sim = [
        "source /home/centos/.bash_profile && "
        "make -C %s run "
        "PROJECT=%s DESIGN=%s "
        "CONFIG_PROJECT=%s CONFIG=%s "
        "SIM_BINARY=%s/%s"
        % (root_dir, project, design, project, config,
           bin_dir, benchmarks[benchmark]["binary"])
        for benchmark in benchmarks
    ]
    ssh.execute_commands(clients, benchmarks, run_sim)

    # Copy sample files
    for client, benchmark in zip(clients, list(benchmarks.keys())):
        sample_file = benchmarks[benchmark]["sample"]
        remote_path = os.path.join(driver_dir, sample_file)
        local_path = os.path.join(full_config, sample_file)
        ssh.get(client, remote_path, local_path)

    ssh.close(clients)
    aws.terminate_instances(instances)

if __name__ == "__main__":
    main()
