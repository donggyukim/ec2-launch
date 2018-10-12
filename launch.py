#!/usr/bin/env python3

import argparse
import os
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

parser = argparse.ArgumentParser()
parser.add_argument(
    "-k", "--key", dest="key", type=str, required=True,
    help="key file")
parser.add_argument(
    "-i", "--input", dest="input", type=str, required=True,
    help="input type [test | ref]")

args = parser.parse_args()

names = [b + "." + args.input for b in SPEC_INT]
count = len(names)
for name in names:
    out_filename = name + ".out"
    err_filename = name + ".err"
    if os.path.exists(out_filename):
        os.remove(out_filename)
    if os.path.exists(err_filename):
        os.remove(err_filename)

# ami = "ami-02cf4b28236606aa5"
ami = "ami-0633862c04a54b7e3"
instances = aws.launch_instances(ami, count=count)
aws.wait_on_instance_launches(instances)

instance_ids = [instance.id for instance in instances]
instance_descs = aws.describe_instances(instance_ids)
clients = ssh.connect_instances(instance_descs, args.key)

afi = "agfi-0fd34e8219d414257" # Rocket

load_afi = [
    "%s && %s %s" % (
        "cd /home/centos/dessert-hdk",
        "./bin/load-afi.sh",
        afi)
    for _ in range(count)
]

design = "Rocket"
# design = "BOOM"
config = "DefaultRocketConfig"
# config = "SmallBoomConfig"

run_sim = [
    "source %s && make -C %s run SIM_BINARY=%s/bblvmlinux-%s DESIGN=%s CONFIG=%s" % (
        "/home/centos/.bash_profile",
        "/home/centos/dessert-hdk",
        "/home/centos/spec2006",
        name, design, config)
    for name in names
]

ssh.execute_commands(names, clients, load_afi)
ssh.execute_commands(names, clients, run_sim)

for client, name in zip(clients, names):
    sample_file = "bblvmlinux-" + name + ".sample"
    local_path = "./%s" % (sample_file)
    remote_path = "/home/centos/dessert-hdk/output/f1/dessert.rocketchip.%s/%s" % (
        config, sample_file)
    ssh.get(client, remote_path, local_path)

ssh.close(clients)
aws.terminate_instances(instances)
