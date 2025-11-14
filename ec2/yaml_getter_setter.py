#!/home/tabsdata/tabsdata-env/bin/python
import yaml, os, argparse, sys


def get_yaml_value(path, key):
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        result = data.get(key)
        return result if type(result) == str else result[0]
    except:
        return "None"


def set_yaml_value(path, key, value, value_type):
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        if value_type == "str":
            data[key] = value
        elif value_type == "list":
            data[key] = [value]
        with open(path, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False)
    except:
        return "None"


def get_process_arg(process, key):
    try:
        process_list = process.split(" --")
        command = process_list.pop(0)
        arg_dict = {i.split(" ")[0]: i.split(" ")[1] for i in process_list}
        value = arg_dict.get(key)
        return str(value)
    except:
        return "None"


def append_yaml_value(path, key, value):
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        current = data.get(key)

        if current is None:
            data[key] = [value]

        elif isinstance(current, str):
            return "None"

        elif isinstance(current, list):
            if value not in current:
                current.append(value)
            data[key] = current

        else:
            return "None"

        with open(path, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False)

        return data[key]

    except Exception:
        return "None"


def main():
    parser = argparse.ArgumentParser(
        prog="yamlz", description="Get or set keys in a YAML file."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    gp = subparsers.add_parser("get", help="Get a key from a YAML file")
    gp.add_argument("--path", required=True)
    gp.add_argument("--key", required=True)

    sp = subparsers.add_parser("set", help="Set a key in a YAML file")
    sp.add_argument("--path", required=True)
    sp.add_argument("--key", required=True)
    sp.add_argument("--value", required=True)
    sp.add_argument("--type", required=True)

    gpa = subparsers.add_parser("get_arg", help="Get an Arg from a Process")
    gpa.add_argument("--path", required=True)
    gpa.add_argument("--key", required=True)

    ap = subparsers.add_parser(
        "append", help="append to a list in a key in a YAML file"
    )
    ap.add_argument("--path", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--value", required=True)

    args = parser.parse_args()

    if args.command == "get":
        result = get_yaml_value(args.path, args.key)
        if result is None:
            print(f"Key '{args.key}' not found in {args.path}")
            sys.exit(1)
        print(result)
    elif args.command == "set":
        value = os.path.expandvars(args.value)
        result = set_yaml_value(args.path, args.key, value, args.type)
        print(f"Updated '{args.key}' = '{value}' in {args.path} {result}")
    elif args.command == "get_arg":
        result = get_process_arg(args.path, args.key)
        print(result)
    elif args.command == "append":
        result = append_yaml_value(args.path, args.key, args.value)
        print(result)


if __name__ == "__main__":
    main()
