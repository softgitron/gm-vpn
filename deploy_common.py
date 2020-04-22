from os import path
import sys
import json


def load_config():
    config = {}
    if path.isfile("./config.json"):
        config_file_name = "config.json"
    else:
        config_file_name = "default_config.json"
    try:
        with open(config_file_name, "r") as config_file:
            config_json = "".join(config_file.readlines())
            config = json.loads(config_json)
    except IOError:
        print("No config file found.")
        sys.exit(1)

    # Check that all required parameters are there
    if not config["names"] or (len(config["names"]) == 0):
        print("No user names supplied.")
        sys.exit(2)
    return config


def save_cofig(file_name, config):
    json_config = json.dumps(config)
    try:
        with open(file_name, "w") as config_file:
            config_file.write(json_config)
    except IOError:
        print("Can't save config file")
        sys.exit(2)
