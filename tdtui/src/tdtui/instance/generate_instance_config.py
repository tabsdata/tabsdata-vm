from InquirerPy import inquirer
from tdtui.core.find_instances import main as find_instances


def identify_instance_name_selection(instances=None):
    if instances == None:
        instances = find_instances()
    existing_instance_names = [i["name"] for i in instances]
    print(existing_instance_names)
    instance_name = inquirer.text(
        message="Please provide a Name for your instance"
    ).execute() 
    if instance_name == "":
        instance_name = "tabsdata"
    while instance_name in existing_instance_names:
        instance_name = inquirer.text(
            message="That name is already in use. Please choose another"
        ).execute()
        if instance_name == "":
            instance_name = "tabsdata"
    print("Thank you, using the name: " + instance_name)
    return instance_name


def identify_port_selections(instance):
    instance_name = instance["name"]
    cfg_ext = instance["cfg_ext"]
    cfg_int = instance["cfg_int"]
    arg_ext = instance["arg_ext"]
    arg_int = instance["arg_int"]
    message = f"""By default, the Tabsdata server {instance_name} is set up on:

    • Port {arg_ext} for external connections
    • Port {arg_int} for internal connections

    Would you like to use the default configuration, or set custom ports?"""
    choices = ["default", "custom"]
    choice = inquirer.select(message, choices)

    if choice == "default":
        external_port = arg_ext.split(":")[-1]
        external_int = arg_int.split(":")[-1]
    else:
        external_port = inquirer.number(
            message="Please provide an External Port"
        ).execute()
        internal_port = inquirer.number(
            message="Please provide an Internal Port"
        ).execute()
    instance["external_port"] = external_port
    instance["internal_port"] = internal_port

    return instance


def validate_port_selections(instance, instances=None):
    if instances == None:
        instances = find_instances()
    used_ports = [i for i in instances if i["status"] == "Running"]
    combined = set().union(*used_ports)
    external_port = instance["external_port"]
    internal_port = instance["internal_port"]

    while external_port in combined:
        owning_instance = [
            i
            for i in instances
            if external_port in [i["external_port"], i["internal_port"]]
        ][0]["name"]
        external_port = inquirer.number(
            message=f"That port is already being used by {owning_instance}. Please choose another"
        ).execute()
    while internal_port in combined:
        owning_instance = [
            i
            for i in instances
            if internal_port in [i["external_port"], i["internal_port"]]
        ][0]["name"]
        internal_port = inquirer.number(
            message=f"That port is already being used by {owning_instance}. Please choose another"
        ).execute()
    instance["external_port"] = external_port
    instance["internal_port"] = internal_port

