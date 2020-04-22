#!/bin/python
from os import system as sexecute
from os import environ
from os import chdir
from os import path
import time
import re
import deploy_common


class Configuration:
    def __init__(self):
        self.config = deploy_common.load_config()
        self.create_key()
        self.deploy_instance()
        time.sleep(30)
        self.get_interface()
        deploy_common.save_cofig("upload_config.json", self.config)
        # self.start_instance_deploy()

    def create_key(self):
        execute("rm id_rsa id_rsa.pub")
        execute('ssh-keygen -b 4096 -C vpn -N "" -f id_rsa')
        with open("id_rsa.pub", "r") as key:
            self.key = key.readline().replace(" ", "\ ")

    def deploy_instance(self):
        deploy = f"""gcloud compute --project={self.config["project_name"]}
instances create {self.config["instance_name"]}
--zone={self.config["zone"]}
--machine-type={self.config["machine"]}
--subnet={self.config["network"]}-subnet
--private-network-ip={self.config["interface_ip"]}
--network-tier=PREMIUM
--metadata=startup-script=apt\ update\ &&\ apt-get\ -y\ install\ git\ screen,ssh-keys=vpn:{self.key}
--can-ip-forward
--maintenance-policy=MIGRATE
--service-account={self.config["service_account"]}
--scopes=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/trace.append
--tags=http-server,https-server
--image=ubuntu-multi-ip-subnet
--image-project={self.config["project_name"]}
--boot-disk-size=10GB
--boot-disk-type=pd-standard
--boot-disk-device-name={self.config["instance_name"]}
--no-shielded-secure-boot
--shielded-vtpm
--shielded-integrity-monitoring
--labels=serial-port-enable=true
--reservation-affinity=any > results.txt"""
        deploy = deploy.replace("\n", " ")
        print(deploy)
        execute(deploy)
        # Retrieve public ip address
        with open("results.txt", "r") as ip_file:
            results = "".join(ip_file.readlines())
        ips = re.findall("\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", results)
        for ip in ips:
            if not ip.startswith("10"):
                self.config["external_ip"] = ip
        print("REMEMBER TO CHECK FIREWALL SETTINGS")

    def get_interface(self):
        execute(
            f'ssh vpn@{self.config["external_ip"]} -i id_rsa -o StrictHostKeyChecking=no "ip address" > results.txt'
        )
        with open("results.txt", "r") as interface_file:
            results = "".join(interface_file.readlines())
        raw_interface_name = re.findall("\d: en.{1,3}:", results)[0]
        self.config["interface"] = raw_interface_name[3:-1]

    def start_instance_deploy(self):
        # https://stackoverflow.com/questions/16721891/single-line-sftp-from-terminal
        execute(
            f"""echo -e 'put ./upload_config.json\nexit\n' | sftp -i id_rsa -o StrictHostKeyChecking=no vpn@{self.config["external_ip"]}:/home/vpn"""
        )
        deploy = f"""ssh vpn@{self.config["external_ip"]} -i id_rsa -o StrictHostKeyChecking=no '
sudo git clone https://github.com/softgitron/gm-vpn.git /root/gm-vpn &&
sudo mv /home/vpn/upload_config.json /root/gm-vpn/config.json &&
sudo screen -S instance-deploy -d -m /root/gm-vpn/instance_deploy.py'"""
        deploy = deploy.replace("\n", " ")
        execute(deploy)


def execute(command):
    print(sexecute(command))


Configuration()
