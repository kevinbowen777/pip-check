#!/usr/bin/env python

"""
pip-check gives you a quick overview of all installed packages and their
update status. Under the hood it calls

    `pip list --outdated --format=columns`

and transforms it into a more user friendly table.

Requires ``pip`` Version 9 or higher!

Installation::

    pip install pip-check

Usage::

    $ pip-check -h
    usage: pip-check [-h] [-a] [-c PIP_CMD] [-l] [-r] [-f] [-H] [-u] [-U]

    A quick overview of all installed packages and their update status.

    optional arguments:
      -h, --help            show this help message and exit
      -a, --ascii           Display as ASCII Table
      -c PIP_CMD, --cmd PIP_CMD
                            The pip executable to run. Default: `pip`
      -l, --local           Show only virtualenv installed packages.
      -r, --not-required    List only packages that are not dependencies of
                            installed packages.
      -f, --full-version    Show full version strings.
      -H, --hide-unchanged  Do not show "unchanged" packages.
      -u, --show-update     Show update instructions for updatable packages.
      -U, --user            Show only user installed packages.
"""
from __future__ import unicode_literals

import argparse
import json
import re
import subprocess
import sys
from collections import OrderedDict
from distutils.version import LooseVersion

import colorclass
import terminaltables

# ------------------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------------------

# Minimum pip version we need
pip_version = 9

# The `pip` command to run. Normally `pip` but you can specify
# it using the `--cmd=pip` argument.
#
# pip-check --cmd=pip3
pip_cmd = "pip"


# The complete command to run to get a JSON list of outdated packages
pip_uptodate_arg = "--uptodate"
pip_outdated_arg = "--outdated"
pip_not_required_arg = "--not-required"
pip_user_arg = "--user"
pip_local_arg = "--local"

check_cmd = (
    "{pip_cmd} list {arg} --format=json {notreq_arg} {user_arg} {local_arg}"
)

# Some pip packages such as pycryptopp have ridiculous long version
# # 0.6.0.1206569328141510525648634803928199668821045408958
# which messes up the table. These are capped by default to 10 characters.
# Can be overridden with -f.
version_length = 10

# Text IO
def windows_out(text):
    """
    Custom stdout for Windows. The colorClass enabler needs
    to be set before every single line.
    """
    colorclass.Windows.enable(auto_colors=True, reset_atexit=True)
    sys.stdout.write(text)


err = sys.stderr.write
out = windows_out if sys.platform == "win32" else sys.stdout.write

# ------------------------------------------------------------------------------


def set_color(options, text, color):
    """
    Little wrapper around Color() to dynamically disable it on demand.
    """
    if options.disable_colors:
        return text

    return colorclass.Color(
        "{{{color}}}{text}{{/{color}}}".format(text=text, color=color)
    )


def check_pip_version(options):
    """
    Make sure minimum pip version is met.
    """
    cmd = "{pip_cmd} --version".format(pip_cmd=options.pip_cmd)

    cmd_response = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    cmd_response_string = cmd_response.stdout.read().decode("utf-8").strip()

    if not cmd_response_string:
        err(
            "The pip command did not return a version string. "
            "Does `pip --version` work for you?"
        )
        sys.exit(1)

    # cmd_version is a string like
    # pip 9.0.1 from /usr/local/lib/python2.7/site-packages (python 2.7)

    matches = re.match(
        r"pip (?P<major>\d+)\.(?P<minor>\d+).*",
        cmd_response_string,
        re.UNICODE,
    )
    if matches and int(matches.groupdict()["major"]) >= pip_version:
        return True

    # Did not meet minimum version
    err(
        "Please update pip. The minimal pip version we require is {v}.".format(
            v=pip_version
        )
    )
    sys.exit(1)


def get_package_versions(options, outdated=True):
    """
    Retrieve a list of outdated packages from pip. Calls:

        pip list [--outdated|--uptodate] --format=json [--not-required] [--user] [--local]
    """
    cmd = check_cmd.format(
        pip_cmd=options.pip_cmd,
        arg=pip_outdated_arg if outdated else pip_uptodate_arg,
        notreq_arg=pip_not_required_arg if options.pip_not_required else "",
        user_arg=pip_user_arg if options.show_user else "",
        local_arg=pip_local_arg if options.show_local else "",
    )
    cmd_response = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    cmd_response_string = cmd_response.stdout.read().decode("utf-8").strip()

    if not cmd_response_string:
        err("No outdated packages. \\o/")
        sys.exit(0)

    try:
        pip_packages = json.loads(cmd_response_string)
    except Exception as e:  # Py2 raises ValueError, Py3 JSONEexception
        err(
            "Unable to parse the version list from pip. "
            "Does `pip list --format=json` work for you?"
        )
        sys.exit(1)

    return pip_packages


def main():
    parser = argparse.ArgumentParser(
        description="A quick overview of all installed packages "
        "and their update status."
    )
    parser.add_argument(
        "-a",
        "--ascii",
        action="store_true",
        dest="ascii_only",
        default=False,
        help="Display as ASCII Table",
    )
    parser.add_argument(
        "-c",
        "--cmd",
        dest="pip_cmd",
        default=pip_cmd,
        help="The pip executable to run. Default: `pip`",
    )
    parser.add_argument(
        "-l",
        "--local",
        action="store_true",
        dest="show_local",
        default=False,
        help="Show only virtualenv installed packages.",
    )
    parser.add_argument(
        "-r",
        "--not-required",
        action="store_true",
        dest="pip_not_required",
        default=False,
        help="List only packages that are not dependencies of installed packages.",
    )
    parser.add_argument(
        "-f",
        "--full-version",
        action="store_true",
        dest="show_long_versions",
        default=False,
        help="Show full version strings.",
    )
    parser.add_argument(
        "-H",
        "--hide-unchanged",
        action="store_true",
        dest="hide_unchanged",
        default=False,
        help='Do not show "unchanged" packages.',
    )
    parser.add_argument(
        "-u",
        "--show-update",
        action="store_true",
        dest="show_update",
        default=False,
        help="Show update instructions for updatable packages.",
    )
    parser.add_argument(
        "-U",
        "--user",
        action="store_true",
        dest="show_user",
        default=False,
        help="Show only user installed packages.",
    )
    parser.add_argument(
        "--disable-colors",
        action="store_true",
        dest="disable_colors",
        default=False,
        help="Disable coloring of text and tables.",
    )
    options = parser.parse_args()

    # The pip check factory
    check_pip_version(options)

    # --------------------------------------------------------------------------

    sys.stdout.write("Loading package versions...\n")
    sys.stdout.flush()

    # Unchanged Packages
    unchanged = []
    if not options.hide_unchanged:
        unchanged = get_package_versions(options, outdated=False)

    packages = {
        "major": [],
        "minor": [],
        "unknown": [],
        "unchanged": unchanged,
    }

    # Fetch all outdated packages and sort them into major/minor/unknown.
    for package in get_package_versions(options, outdated=True):

        # No version info
        if not "latest_version" in package or not "version" in package:
            packages["unknown"].append(package)
            continue

        try:
            latest = LooseVersion(package["latest_version"])
            current = LooseVersion(package["version"])
        except ValueError:
            # Unable to parse the version into anything useful
            packages["unknown"].append(package)
            continue

        # If the current version is larger than the latest
        # (e.g. a pre-release is installed) put it into the unknown section.
        # Technically its 'unchanged' but I guess its better to have
        # pre-releases stand out more.
        if current > latest:
            packages["unknown"].append(package)
            continue

        # Current and latest package version is the same. If this happens,
        # it's likely a bug with the version parsing.
        if current == latest:
            packages["unchanged"].append(package)
            continue

        # Major upgrade (first version number)
        if latest.version[0] > current.version[0]:
            packages["major"].append(package)
            continue

        # Everything else is a minor update
        packages["minor"].append(package)

    table_data = OrderedDict()

    def cut_version(version):
        if not version or version == "Unknown":
            return version

        # Cut version to readable length
        if (
            not options.show_long_versions
            and len(version) > version_length + 3
        ):
            return "{0}...".format(version[:version_length])
        return version

    def columns(package):
        # Generate the columsn for the table(s) for each package
        # Name | Current Version | Latest Version | pypi String

        name = package.get("name")
        current_version = package.get("version", None)
        latest_version = package.get("latest_version", None)
        help_string = "https://pypi.python.org/pypi/{}".format(package["name"])

        if latest_version and options.show_update:
            help_string = "pip install {name}=={version}".format(
                name=name, version=latest_version
            )

        return [
            name,
            cut_version(current_version) or "Unknown",
            cut_version(latest_version) or current_version or "Unknown",
            help_string,
        ]

    for key, label, color in [
        ("major", "Major Release Update", "autored"),
        ("minor", "Minor Release Update", "autoyellow"),
        ("unchanged", "Unchanged Packages", "autogreen"),
        ("unknown", "Unknown Package Release Status", "autoblack"),
    ]:
        if packages[key]:
            if not key in table_data:
                table_data[key] = []

            colored_label = set_color(options, label, color)

            table_data[key].append([colored_label, "Version", "Latest"]),
            for package in packages[key]:
                table_data[key].append(columns(package))

    # Table output class
    Table = (
        terminaltables.AsciiTable
        if options.ascii_only
        else terminaltables.SingleTable
    )

    for key, data in table_data.items():
        out("\n")
        table = Table(data)
        out(table.table)
        out("\n")
        sys.stdout.flush()

    if options.show_update:
        for label in ("major", "minor"):
            if packages[label]:
                out(
                    "\nTo update all {label} releases run:\n\n"
                    "  {pip_cmd} install -U {packages}\n".format(
                        label=label,
                        pip_cmd=options.pip_cmd,
                        packages=" ".join(
                            [p["name"] for p in packages[label]]
                        ),
                    )
                )


# ------------------------------------------------------------------------------

if __name__ == "__main__":
    main()
