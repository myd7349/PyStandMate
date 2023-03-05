#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import collections
import fnmatch
import os
from pathlib import Path
from pprint import pprint
import re
import shutil
import sys
import subprocess
import urllib.parse
import urllib.request
import zipfile


EmbedPython = collections.namedtuple("EmbedPython", ["url", "filename"])


DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8"


def fetch_page(url, encoding="utf-8"):
    request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    response = urllib.request.urlopen(request)

    if encoding:
        charset = response.headers.get_content_charset(failobj=encoding)
        for line in response:
            yield line.decode(charset)
    else:
        yield from response


def fetch_page_contents(url, encoding="utf-8"):
    return "".join(fetch_page(url, encoding))


def find_urls(s):
    return re.findall(r'href=[\'"]?([^\'" >]+)', s)


def get_embed_python_versions():
    page_contents = fetch_page_contents("https://www.python.org/downloads/windows/")
    dload_urls = find_urls(page_contents)

    result = collections.OrderedDict()

    for url in dload_urls:
        url_parts = urllib.parse.urlparse(url)
        if fnmatch.fnmatch(url_parts.path, "*embed*.zip"):
            version = url_parts.path.split("-")[1]
            embed_python = EmbedPython(url, Path(url_parts.path).name)
            if not version in result:
                result[version] = [embed_python]
            else:
                result[version].append(embed_python)

    return result


def download_embed_python(version, bitness, target_dir):
    arch = "win32" if bitness == 32 else "amd64"
    filename = f"python-{version}-embed-{arch}.zip"
    embed_python_path = target_dir / filename

    if not embed_python_path.is_file():
        print(f"{embed_python_filename} doesn't exist, will download it first.")

        print("Get available Windows embeddable Python packages...")
        versions = get_embed_python_versions()

        if version not in versions:
            print(f"Couldn't find embeddable Python package of version {version}.")
            print("Available versions:")
            pprint(versions.keys())
            sys.exit(1)

        file_list = versions[args.python_version]
        for embed_python in file_list:
            if arch in embed_python.filename:
                print(f"Download {embed_python.url} -> {embed_python.filename}...")
                urllib.request.urlretrieve(embed_python.url, embed_python_path)
                break

    if not embed_python_path.is_file():
        print(f"Couldn't find a suitable version of embeddable Python.")
        sys.exit(2)

    return embed_python_path


def install_pip(embed_python_dir, get_pip_path, env):
    print("Uncomment import site...")
    pth_file = tuple(embed_python_dir.glob("*._pth"))[0]
    with open(pth_file, "r") as fp:
        pth_file_content = fp.read()
    pth_file_content = pth_file_content.replace("#import site", "import site")
    with open(pth_file, "w") as fp:
        fp.write(pth_file_content)

    print("Install pip...")
    python = embed_python_dir / "python.exe"
    # subprocess.run([python, get_pip_path])
    subprocess.run(["cmd", "/C", python, get_pip_path], env=env, check=True)


def install_package(embed_python_dir, package, env):
    python = embed_python_dir / "python.exe"
    # subprocess.run(['cmd', '/C', embed_python_dir / 'Scripts' / 'pip.exe', 'install', package], env=env)
    subprocess.run(
        ["cmd", "/C", python, "-m", "pip", "install", package], env=env, check=True
    )


def install_requirements(embed_python_dir, requirements_file, env):
    python = embed_python_dir / "python.exe"
    subprocess.run(
        ["cmd", "/C", python, "-m", "pip", "install", "-r", requirements_file],
        env=env,
        check=True,
    )


def install_packages(embed_python_dir, packages, env):
    for package in packages:
        if Path(package).name == "requirements.txt":
            install_requirements(embed_python_dir, package, env)
        else:
            install_package(embed_python_dir, package, env)


def main():
    script_path = Path(sys.argv[0])
    script_dir = script_path.parent

    parser = argparse.ArgumentParser(
        prog=script_path.stem,
        description="PyStand Bootstrap.",
    )

    parser.add_argument("--python-version", default="3.8.10", help="Python version")
    parser.add_argument("--bitness", choices=(32, 64), default=32, help="Bitness")
    parser.add_argument(
        "--package", nargs="+", help="A list of 3rd-party packages to be installed"
    )

    args = parser.parse_args()

    embed_python_path = download_embed_python(
        args.python_version, args.bitness, script_dir
    )

    if not args.package:
        sys.exit(0)

    embed_python_dir = script_dir / embed_python_path.stem
    print(f"Extract {embed_python_path.name} -> {embed_python_dir.name}...")
    with zipfile.ZipFile(embed_python_path, "r") as zip_ref:
        zip_ref.extractall(embed_python_dir)

    get_pip_path = script_dir / "get-pip.py"
    if not get_pip_path.is_file():
        print("Download get-pip.py...")
        urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", get_pip_path)

    python_scripts_dir = embed_python_dir / "Scripts"
    # Fatal Python error: _Py_HashRandomization_Init: failed to get random numbers to initialize Python
    # env = {'PATH': f'{embed_python_dir}{os.pathsep}{python_scripts_dir}'}
    env = os.environ
    env["PATH"] += os.pathsep + str(python_scripts_dir)

    target_get_pip_path = embed_python_dir / "get-pip.py"
    shutil.copyfile(get_pip_path, target_get_pip_path)
    install_pip(embed_python_dir, target_get_pip_path, env)

    print("Install packages...")
    install_packages(embed_python_dir, args.package, None)


if __name__ == "__main__":
    main()


# Format code:
# pip install black
# black PyStandInit.py

# References:
# [Regular expression to extract URL from an HTML link](https://stackoverflow.com/questions/499345/regular-expression-to-extract-url-from-an-html-link)
# [Unzipping files in Python](https://stackoverflow.com/questions/3451111/unzipping-files-in-python)
# https://gist.github.com/myd7349/9f7c6334e67d1aee68a722a15df4a62a
# [Replace string within file contents](https://stackoverflow.com/questions/4128144/replace-string-within-file-contents)
# https://docs.python.org/3.11/library/pathlib.html
# [Could not find a version that satisfies the requirement setuptools](https://github.com/pypa/pip/issues/7730)
# [How to run a pip install command from a subproces.run()](https://stackoverflow.com/questions/69345839/how-to-run-a-pip-install-command-from-a-subproces-run)
# [How can I Install a Python module within code?](https://stackoverflow.com/questions/12332975/how-can-i-install-a-python-module-within-code)
# [How to run `pip` in a virtualenv with subprocess.check_call()?](https://stackoverflow.com/questions/28574058/how-to-run-pip-in-a-virtualenv-with-subprocess-check-call)
# [Python: Platform independent way to modify PATH environment variable](https://stackoverflow.com/questions/1681208/python-platform-independent-way-to-modify-path-environment-variable)
# [Check if Python Package is installed](https://stackoverflow.com/questions/1051254/check-if-python-package-is-installed)

# Issues:
# 1. python PyStandInit.py --package parse
