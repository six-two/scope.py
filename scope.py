#!/usr/bin/env python3
import argparse
import ipaddress
import os
import socket
import sys
from typing import Any
# pip install pyyaml
import yaml

FILE = os.path.expanduser("~/.pentest/scope.yaml")
DEFAULT_START = {
    "scope": []
}

# TODO proper handling of single ip, network, domain, subdomains
# TODO implement lookup caches
# TODO implement exclude list
# TODO implement check subcommand


def readFile(path: str, defaults: Any) -> Any:
    if os.path.exists(path):
        with open(path, "rb") as f:
            return yaml.safe_load(f) or defaults
    else:
        return defaults


def writeFile(path: str, data: Any) -> None:
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f)


def parse_args() -> Any:
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--project", help="path to the project file", default=FILE)
    sp = ap.add_subparsers(dest="command", required=True)
    # Add subcommand
    add_parser = sp.add_parser("add")
    add_parser.add_argument("scope")
    # Remove subcommand
    remove_parser = sp.add_parser("remove")
    remove_parser.add_argument("scope")
    # Show subcommand
    show_parser = sp.add_parser("show")
    show_parser.add_argument("--ip", action="store_true", help="try resolving hostnames to IP addresses")
    show_parser.add_argument("--name", action="store_true", help="try resolving IP addresses to hostnames")
    return ap.parse_args()


class ScopePy:
    def __init__(self, state_file: str) -> None:
        self.state_file = state_file
        self.state = DEFAULT_START

    def __enter__(self) -> Any:
        self.state = readFile(self.state_file, self.state)
        return self.state

    def __exit__(self, type, value, traceback) -> None:
        writeFile(self.state_file, self.state)


def is_ip_address(possible_ip_address: str) -> bool:
    try:
        ipaddress.ip_address(possible_ip_address)
        return True
    except ValueError:
        return False


def is_ip_network(possible_ip_network: str) -> bool:
    try:
        ipaddress.ip_network(possible_ip_network)
        return True
    except ValueError:
        return False


def command_add(state: Any, args: Any) -> int:
    scope = state.get("scope", [])
    scope.append(args.scope)
    state["scope"] = sorted(set(scope))
    return 0


def print_ip_to_hostname(item: str) -> None:
    try:
        name, aliases, _ips = socket.gethostbyaddr(item)
        message = str(name)
        if aliases:
            message += "(" + ", ".join(aliases) + ")"
        print(message)
    except:
        print("Failed to resolve:", item)


def command_show(state: Any, args: Any) -> int:
    for item in state["scope"]:
        is_item_ip = is_ip_address(item) or is_ip_network(item)
        if args.ip and not is_item_ip:
            try:
                print(socket.gethostbyname(item))
            except:
                print("Failed to resolve:", item)
        elif args.name and is_item_ip:
            if is_ip_network(item):
                network = ipaddress.ip_network(item)
                for ip in network.hosts():
                    print_ip_to_hostname(ip)
            else:
                print_ip_to_hostname(item)
            
        else:
            print(item)
    return 0


def command_remove(state: Any, args: Any) -> int:
    scope = state.get("scope", [])
    if args.scope in scope:
        scope_set = set(scope)
        scope_set.remove(args.scope)
        scope = sorted(scope_set)
    else:
        print("Not in scope:", args.scope)
    state["scope"] = scope
    return 0


def main() -> int:
    args = parse_args()
    project_file = args.project
    cmd = args.command
    print("Using project file:", project_file)
    
    with ScopePy(project_file) as state:
        if cmd == "add":
            return command_add(state, args)
        elif cmd == "remove":
            return command_remove(state, args)
        elif cmd == "show":
            return command_show(state, args)
        else:
            print("Unknown command:", cmd)
            return 1


if __name__ == "__main__":
    try:
        code = main()
        sys.exit(code)
    except KeyboardInterrupt:
        print("[Ctrl-C]")
