import subprocess
from tdtui.core.subprocess_runner import run_bash
from yaspin import yaspin
from yaspin.spinners import Spinners
import time
from tdtui.core.yaml_getter_setter import set_yaml_value
from tdtui.core.find_instances import define_root
from tdtui.instance.generate_instance_config import identify_instance_name_selection, validate_port_selections, identify_port_selections
from tdtui.core.find_instances import main as find_instances
from tdtui.instance.display_instances import display_instances_rich



def set_config_yaml(instance, ip_address="127.0.0.1"):
    instance_name = instance['name']
    external_port = instance['external_port']
    internal_port = instance['insternal_port']
    config_yaml_path = define_root(instance_name, "workspace/config/proc/regular/apiserver/config/config.yaml")
    set_yaml_value(path=config_yaml_path,key="addresses",value=f"{ip_address}:{external_port}")
    set_yaml_value(path=config_yaml_path,key="internal_addresses",value=f"{ip_address}:{internal_port}")
    return


def start_instance(instance):
    instance_name = instance["name"]
    with yaspin().bold.blink.bouncingBall.on_cyan as sp:
        run_bash(f"tdserver start --instance {instance_name}")
    display_instances_rich()
    return None



def stop_instance(instance):
    instance_name = instance["name"]
    with yaspin().bold.blink.bouncingBall.on_cyan as sp:
        run_bash(f"tdserver stop --instance {instance_name}")
    display_instances_rich()
    return None


def create_instance():
    instances = find_instances()
    instance_name = identify_instance_name_selection(instances=instances)
    with yaspin().bold.blink.bouncingBall.on_cyan as sp:
        run_bash(f"tdserver create --instance {instance_name}")
    display_instances_rich()
    return None

def delete_instance(instance):
    instance_name = instance["name"]
    with yaspin().bold.blink.bouncingBall.on_cyan as sp:
        run_bash(f"tdserver delete --instance {instance_name} --force")
    display_instances_rich()
    return None

