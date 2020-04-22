# gm-vpn

Automatic VPN and Mumble deployment to g-cloud

## About this project

This is a hobby project that automatically deploys [level 2 Openvpn server](https://openvpn.net/community-resources/ethernet-bridging/) to the Google cloud with maximum ip forwarding. This project was made because there were very big networking problems with couple of multiplayer games due to nat. VPN tunnel that is deployed by this project should provide ulta stable and low latency VPN that should provide perfectly stable multiplayer experience even in worst networking conditions.

## Quick start

This script is pretty hard to setup since it is not fully automatic. Follow all the points told bellow excatly

1. Create account to goole cloud
   - [Google cloud](https://cloud.google.com/)
2. Install openssh, git and gcloud command to your linux machine
   - [gcloud install](https://cloud.google.com/sdk/install)
   - run `gcloud init` to setup command properly
3. Configure network in Google cloud
   - Go to [VPC network site](https://console.cloud.google.com/networking/networks)
   - Create new VPC network
   - Network name _gm-vpn-network_
   - Subnet name _gm-vpn-subnet_
   - Region _europe-north1_
   - Ip address range _10.144.0.0/16_
   - Private Google access _off_
   - Flow logs _on_
   - Dynamic routing mode _regional_
   - DNS server policy _No server policy_
4. Configure firewall in Google cloud
   - [VPC firewall](https://console.cloud.google.com/networking/firewalls)
   - Add firewall rules to allow traffic on tcp ports 22, 80 and 443
   - Create firewall rule
   - Name _gm-vpn-firewall_
   - Network _gm-vpn-network_
   - Targets _all instances in network_
   - IP ranges _0.0.0.0/0_
   - Specified protocols and ports _tcp 22, 80, 443_
5. Create multi ip image
   - This is necessary to give instance multiple ip addresses and make the system work.
   - Run command in the cloud console (can be found from up right): `gcloud compute images create ubuntu-multi-ip-subnet --source-image projects/ubuntu-os-cloud/global/images/ubuntu-minimal-1910-eoan-v20200406 --storage-locationeurope-north1 --guest-os-features MULTI_IP_SUBNET`
   - More info available for this command [here](https://cloud.google.com/vpc/docs/create-use-multiple-interfaces#i_am_having_connectivity_issues_when_using_a_netmask_that_is_not_32) and [here](https://cloud.google.com/sdk/gcloud/reference/alpha/compute/images/create)
6. Prepare deployer
   - clone the repo
   - `git clone https://github.com/softgitron/gm-vpn.git`
   - Copy default_config.json to config.json
   - Change your personal project name to json
   - Project name can be found from Google cloud main page
   - Put Project ID to project_name field in json
   - Find your service account from [IAM panel](https://console.cloud.google.com/iam-admin/iam)
   - Correct service account should have name like _#########-compute@developper.gserviceaccount.com_
   - Put service account to service_account field in json
   - Change _names_ field to your liking. By default there is only three clients
7. Run deployer
   - Start deployer by running `./deploy.py`
   - This script should now do the rest
   - Wait some time before trying to connect
   - It can take up to 5 minutes before VPN is up
   - After the client side (not instance side) script has completed last thing it prints should be ip address
   - This ip address can be used to access instance if anything goes wrong (`ssh address@printed_ip -i id_rsa`)
8. Setup VPN connection from Windows
   - Download openvpn client from [Openvpn site](https://openvpn.net/community-downloads/) (Windows 10/Server 2016...)
   - Go to external ip address that was shown on the console with web browser
   - Download and extract zip that is in the site
   - Start Openvpn
   - Openvpn should start in the right on the taskbar.
   - Right click Openvpn icon and click Import from file
   - Select any of the files inside zip
   - Right click Openvpn icon and press connect
   - If everything goes well you should have now full connection to vpn
   - You can check the situation by accessing [speedtest.net](speedtest.net) for example
   - Website should now show that you are from Google cloud platform
   - Note if you want to give access to your friends only part 8 is required for them

## Mumble server

This script installs also [mumble](https://wiki.mumble.info/wiki/Main_Page) server to the instance. Mumble server should be accessible by default in _10.144.2.2_ address

## Help?

If someone ever tries to set this up free to contact me. This script is not very robust for errors so everything must be done precisely.

### Development time

It took me four days and three nights to develop this script into working condition.
