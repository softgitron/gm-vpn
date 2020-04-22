#!/bin/bash

KEY_DIR=/etc/openvpn
OUTPUT_DIR=./clients
BASE_CONFIG=./client.conf
cat ${BASE_CONFIG} \
    <(echo -e '<ca>') \
    ${KEY_DIR}/ca.crt \
    <(echo -e '</ca>\n<cert>') \
    ${KEY_DIR}/${1}.crt \
    <(echo -e '</cert>\n<key>') \
    ${KEY_DIR}/${1}.key \
    <(echo -e '</key>') \
    > ${OUTPUT_DIR}/${1}.ovpn