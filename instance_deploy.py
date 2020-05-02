#!/bin/python3

from os import system as sexecute
from os import environ
from os import chdir
from os import path
import deploy_common
import re
import json
import sys


class Configuration:
    def __init__(self):
        chdir("/root/gm-vpn")
        self.config = deploy_common.load_config()
        self.main_vpn_installation()
        self.edit_vpn_config()
        self.create_bridge()
        self.create_client_files()
        # Finally start vpn server
        execute("systemctl start openvpn@server")
        self.setup_mumble()

    def main_vpn_installation(self):
        # Install openvpn, mumble server and utils
        execute(
            "apt -y install openvpn easy-rsa iptables bridge-utils net-tools zip mumble-server"
        )
        execute("rm -rf /etc/openvpn/easy-rsa/")
        execute("mkdir /etc/openvpn/easy-rsa/")
        execute("cp -r /usr/share/easy-rsa/* /etc/openvpn/easy-rsa/")

        # Set environment details
        environ["KEY_COMMON_NAME"] = "gm-VPN"
        environ["KEY_COUNTRY"] = "FI"
        environ["KEY_PROVINCE"] = "EK"
        environ["KEY_CITY"] = "Lappeenranta"
        environ["KEY_ORG"] = "gm-VPN"
        environ["KEY_EMAIL"] = "gm-VPN@example.com"
        environ["KEY_CN"] = "gm-VPN-key"
        environ["KEY_ALTNAMES"] = "gm"
        environ["KEY_NAME"] = "gm-VPN"
        environ["KEY_OU"] = "gm-VPN"
        environ["EASYRSA_EXT_DIR"] = "/etc/openvpn/easy-rsa/x509-types"

        # Initialize keys
        chdir("/etc/openvpn/easy-rsa")
        execute("./easyrsa init-pki")
        execute("./easyrsa gen-dh")
        execute("echo " " | ./easyrsa gen-req server nopass")
        execute('echo "" | ./easyrsa build-ca nopass')
        execute('echo "yes" | ./easyrsa sign-req server server')

        for name in self.config["names"]:
            execute(f'echo "" | ./easyrsa gen-req {name} nopass')
            execute(f'echo "yes" | ./easyrsa sign-req client {name}')

    def edit_vpn_config(self):
        execute("openvpn --genkey --secret tiv.key")
        execute("cp ./tiv.key /etc/openvpn")
        execute("cp /etc/openvpn/easy-rsa/pki/issued/server.crt /etc/openvpn/")
        execute("cp /etc/openvpn/easy-rsa/pki/ca.crt /etc/openvpn/")
        execute("cp /etc/openvpn/easy-rsa/pki/private/server.key /etc/openvpn/")
        # execute("cp /etc/openvpn/easy-rsa/pki/dh.pem /etc/openvpn/")
        execute("openssl dhparam -dsaparam -out /etc/openvpn/easy-rsa/pki/dh.pem 2048")
        for name in self.config["names"]:
            execute(f"cp /etc/openvpn/easy-rsa/pki/private/{name}.key /etc/openvpn/")
            execute(f"cp /etc/openvpn/easy-rsa/pki/issued/{name}.crt /etc/openvpn/")

        # Edit configuration
        go_home_dir()
        execute("git clone https://github.com/OpenVPN/openvpn.git")
        execute(
            "cp ./openvpn/sample/sample-config-files/server.conf /etc/openvpn/server.conf"
        )
        chdir("/etc/openvpn")
        openvpn_config = self.load_openvpn_config("/etc/openvpn/server.conf")
        openvpn_config["proto"] = "tcp"
        # Should fix anoying packet dropping
        openvpn_config["tcp-queue-limit"] = "256"
        openvpn_config["dev"] = "tap0"
        openvpn_config["ca"] = "ca.crt"
        openvpn_config["cert"] = "server.crt"
        openvpn_config["key"] = "server.key"
        openvpn_config["dh"] = "dh.pem"
        openvpn_config["verb"] = "5"
        del openvpn_config["server"]
        openvpn_config[
            "server-bridge"
        ] = f'{self.config["interface_ip"]} {self.config["interface_netmask"]} {self.config["vpn_start_ip"]} {self.config["vpn_end_ip"]}'
        openvpn_config["port"] = "443"
        openvpn_config["client-to-client"] = ""
        openvpn_config["user"] = "nobody"
        openvpn_config["group"] = "nogroup"
        openvpn_config["cipher"] = "AES-256-CBC"
        openvpn_config["auth"] = "SHA256"
        del openvpn_config["explicit-exit-notify"]
        del openvpn_config["tls-auth"]
        openvpn_config[
            "push1"
        ] = f'"redirect-gateway {self.config["interface_gateway"]}"'
        openvpn_config["push2"] = f'"route-gateway {self.config["interface_gateway"]}"'
        openvpn_config["push3"] = '"dhcp-option DNS 8.8.8.8"'
        openvpn_config["push4"] = '"dhcp-option DNS 8.8.4.4"'
        openvpn_config[
            "push5"
        ] = f'"route 0.0.0.0 0.0.0.0 {self.config["interface_gateway"]}"'
        self.save_openvpn_config("/etc/openvpn/server.conf", openvpn_config)

    def create_bridge(self):
        # count = len(self.config["names"])
        count = 1
        interface = self.config["interface"]
        interface_ip = self.config["interface_ip"]
        interface_gateway = self.config["interface_gateway"]
        interface_netmask = self.config["interface_netmask"]
        interface_broadcast = self.config["interface_broadcast"]

        for i in range(count):
            execute(f"openvpn --mktun --dev tap{i}")
        execute("brctl addbr br0")
        execute(f"brctl addif br0 {interface}")
        for i in range(count):
            execute(f"brctl addif br0 tap{i}")
        for i in range(count):
            execute(f"ifconfig tap{i} 0.0.0.0 promisc up")
        execute(f"ifconfig {interface} 0.0.0.0 promisc up")
        execute(
            f"ifconfig br0 {interface_ip} netmask {interface_netmask} broadcast {interface_broadcast}"
        )
        execute(
            f"ip route add default via {interface_gateway} dev br0 proto dhcp src {interface_ip}"
        )
        self.configure_sysctl()
        execute(
            'echo "DNS=8.8.8.8\nFallbackDNS=1.1.1.1\n" >> /etc/systemd/resolved.conf'
        )
        execute("systemctl restart systemd-resolved")
        # Secret sauce to get this thing actually working on gcloud
        execute(f"iptables -t nat -A POSTROUTING -o br0 -j SNAT --to {interface_ip}")

    def configure_sysctl(self):
        # Enable traffic forwarding
        execute('echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf')
        # https://www.cyberciti.biz/faq/linux-tcp-tuning/
        # Fix tcp buffer issues
        # Set max buffer size to 12MiB. This is propably bit too large
        execute("echo 'net.core.wmem_max=12582912' >> /etc/sysctl.conf")
        execute("echo 'net.core.rmem_max=12582912' >> /etc/sysctl.conf")
        execute("echo 'net.ipv4.tcp_rmem= 10240 87380 12582912' >> /etc/sysctl.conf")
        execute("echo 'net.ipv4.tcp_wmem= 10240 87380 12582912' >> /etc/sysctl.conf")
        execute("echo 'net.core.netdev_max_backlog = 5000' >> /etc/sysctl.conf")
        execute("sysctl -p /etc/sysctl.conf")
        execute(f"ip link set {self.config['interface']} txqueuelen 5000")

    def create_client_files(self):
        go_home_dir()
        chdir("./gm-vpn")
        # create base config
        execute("mkdir /root/gm-vpn/clients")
        execute("cp ../openvpn/sample/sample-config-files/client.conf ./")
        client_config = self.load_openvpn_config("./client.conf")
        client_config["dev"] = "tap"
        client_config["proto"] = "tcp"
        client_config["remote"] = self.config["external_ip"] + " " + self.config["port"]
        client_config["redirect-gateway"] = "autolocal"
        client_config["route-metric"] = "1"
        client_config["cipher"] = "AES-256-CBC"
        client_config["auth"] = "SHA1"
        del client_config["tls-auth"]
        del client_config["ca"]
        del client_config["cert"]
        del client_config["key"]
        self.save_openvpn_config("./client.conf", client_config)
        for name in self.config["names"]:
            execute(f"./gen-client-config.sh {name}")
        execute("zip -r clients.zip clients")
        execute("mv clients.zip clients")
        for name in self.config["names"]:
            execute(f"rm clients/{name}.ovpn")
        chdir("clients")
        execute("screen -S ovpn-server -d -m ../serve_file.py")

    def setup_mumble(self):
        mumble_config = self.load_mumble_config("/etc/mumble-server.ini")
        mumble_config[
            "welcometext"
        ] = '"<br />Welcome to this server running on <b>gm-vpn</b>.<br />Enjoy stable networking!<br />"'
        mumble_config["bandwidth"] = "130000"
        self.save_mumble_config("/etc/mumble-server.ini", mumble_config)
        execute("systemctl start mumble-server")

    def load_openvpn_config(self, file_name):
        openvpn_config = {}
        try:
            with open(file_name, "r") as config_file:
                for line in config_file:
                    if (
                        line.startswith("#")
                        or line.startswith(";")
                        or line.startswith("\n")
                    ):
                        continue
                    splitted = line.split(" ")
                    key = splitted[0]
                    args = " ".join(splitted[1:])
                    openvpn_config[key] = args

        except IOError:
            print("No openvpn config file found.")
            sys.exit(2)
        return openvpn_config

    def save_openvpn_config(self, file_name, openvpn_configs):
        try:
            with open(file_name, "w") as config_file:
                for key in openvpn_configs:
                    if re.search(r"\d+$", key) is not None:
                        config_file.write(f"{key[:-1]} {openvpn_configs[key]}\n")
                    else:
                        config_file.write(f"{key} {openvpn_configs[key]}\n")
        except IOError:
            print("Error during writing to openvpn file")
            sys.exit(3)

    def load_mumble_config(self, file_name):
        openvpn_config = {}
        try:
            with open(file_name, "r") as config_file:
                for line in config_file:
                    if (
                        line.startswith("#")
                        or line.startswith(";")
                        or line.startswith("\n")
                    ):
                        continue
                    splitted = line.split("=")
                    key = splitted[0]
                    args = " ".join(splitted[1:])
                    openvpn_config[key] = args

        except IOError:
            print("No openvpn config file found.")
            sys.exit(2)
        return openvpn_config

    def save_mumble_config(self, file_name, mumble_configs):
        try:
            with open(file_name, "w") as config_file:
                for key in mumble_configs:
                    config_file.write(f"{key}={mumble_configs[key]}\n")
        except IOError:
            print("Error during writing to openvpn file")
            sys.exit(3)


def execute(command):
    print(sexecute(command))


def go_home_dir():
    chdir(path.expanduser("~"))


Configuration()
