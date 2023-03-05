#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Usage:
# PyStandInit.py --help
# PyStandInit.py --response-file PyStandInit.rsp
# PyStandInit.py --bitness 32 --compiler MSVC --python-version 3.8.10 --console

import argparse
import collections
import os
from pathlib import Path
from pprint import pprint
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile


EmbedPython = collections.namedtuple("EmbedPython", ["url", "filename"])

DOWNLOAD_DIR = "download"
BUILD_DIR = "build"
PUBLISH_DIR = "publish"

DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8"


class LoadFromFile(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        with values as f:
            # parse arguments in the file and store them in the target namespace
            parser.parse_args(f.read().split(), namespace)


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


def download_pystand(version, target_dir):
    if version.startswith("v") or version.startswith("V"):
        version = version[1:]

    filename = f"PyStand-v{version}-exe.zip"
    pystand_path = target_dir / filename

    if not pystand_path.is_file():
        if not target_dir.is_dir():
            print(f"Create directory {target_dir}...")
            target_dir.mkdir()

        dload_url = f"https://github.com/skywind3000/PyStand/releases/download/{version}/{filename}"
        print(f"Download {dload_url} -> {filename}...")
        urllib.request.urlretrieve(dload_url, pystand_path)

    return pystand_path


def get_pystand_subdir(compiler, bitness, is_console):
    subsystem = "CLI" if is_console else "GUI"

    if compiler == "MSVC":
        arch = "Win32" if bitness == 32 else "x64"
    else:
        arch = "mingw32" if bitness == 32 else "mingw64"

    return f"PyStand-{arch}-{subsystem}"


def get_pystand_publish_subdir(version, compiler, bitness, is_console):
    if version.startswith("v") or version.startswith("V"):
        version = version[1:]

    subdir = get_pystand_subdir(compiler, bitness, is_console)
    subdir = subdir.replace("PyStand", f"PyStand-v{version}")

    return subdir


def get_embed_python_versions():
    page_contents = fetch_page_contents("https://www.python.org/downloads/windows/")
    dload_urls = find_urls(page_contents)

    result = collections.OrderedDict()

    for url in dload_urls:
        url_parts = urllib.parse.urlparse(url)
        if Path(url_parts.path).match("*embed*.zip"):
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
        print(f"{filename} doesn't exist, will download it first.")

        print("Get available Windows embeddable Python packages...")
        embed_python_versions = get_embed_python_versions()

        if version not in embed_python_versions:
            print(f"Couldn't find embeddable Python package of version {version}.")
            print("Available versions:")
            pprint(tuple(embed_python_versions.keys()))
            sys.exit(1)

        if not target_dir.is_dir():
            print(f"Create directory {target_dir}...")
            target_dir.mkdir()

        embed_python_list = embed_python_versions[version]
        for embed_python in embed_python_list:
            if arch in embed_python.filename:
                print(f"Download {embed_python.url} -> {embed_python.filename}...")
                urllib.request.urlretrieve(embed_python.url, embed_python_path)
                break

    if not embed_python_path.is_file():
        print(f"Couldn't find a suitable version of embeddable Python.")
        sys.exit(2)

    return embed_python_path


def install_pip(embed_python_dir, get_pip_path):
    pth_files = tuple(embed_python_dir.glob("*._pth"))
    if pth_files:
        if len(pth_files) != 1:
            print("There are more than one ._pth files:")
            pprint(pth_files)
            sys.exit(3)

        pth_file = pth_files[0]

        print("Uncomment import site...")

        with open(pth_file, "r") as fp:
            pth_file_content = fp.read()

        pth_file_content = pth_file_content.replace("#import site", "import site")
        with open(pth_file, "w") as fp:
            fp.write(pth_file_content)

    print("Install pip...")
    python = embed_python_dir / "python.exe"
    # subprocess.run([python, get_pip_path])
    subprocess.run(["cmd", "/C", python, get_pip_path], check=True)


def install_package(embed_python_dir, package):
    python = embed_python_dir / "python.exe"
    subprocess.run(["cmd", "/C", python, "-m", "pip", "install", package], check=True)


def install_requirements(embed_python_dir, requirements_file):
    python = embed_python_dir / "python.exe"
    subprocess.run(
        ["cmd", "/C", python, "-m", "pip", "install", "-r", requirements_file],
        check=True,
    )


def install_packages(embed_python_dir, packages):
    for package in packages:
        if "requirements.txt" in Path(package).name:
            install_requirements(embed_python_dir, package)
        else:
            install_package(embed_python_dir, package)


def main():
    script_path = Path(sys.argv[0])
    script_dir = script_path.parent

    parser = argparse.ArgumentParser(
        prog=script_path.stem,
        description="PyStand Bootstrap.",
    )

    parser.add_argument("--pystand-version", default="1.0.11", help="PyStand version")
    parser.add_argument(
        "--bitness", type=int, choices=(32, 64), default=32, help="Bitness"
    )
    parser.add_argument(
        "--compiler", choices=("MSVC", "GCC"), default="MSVC", help="Compiler"
    )
    parser.add_argument(
        "--console", action="store_true", help="Use PyStand CLI instead of GUI"
    )
    parser.add_argument("--python-version", default="3.8.10", help="Python version")
    parser.add_argument(
        "--package", nargs="+", help="A list of 3rd-party packages to be installed"
    )
    parser.add_argument(
        "--response-file",
        type=open,
        action=LoadFromFile,
        help="Read options stored in a response file",
    )

    args = parser.parse_args()

    # 1. Download PyStand
    pystand_path = download_pystand(args.pystand_version, script_dir / DOWNLOAD_DIR)

    # 2. Extract PyStand
    pystand_dir = script_dir / BUILD_DIR / pystand_path.stem
    print(f"Extract {pystand_path.name} -> {pystand_dir.name}...")
    with zipfile.ZipFile(pystand_path, "r") as zip_ref:
        zip_ref.extractall(pystand_dir)

    # 3. Download Python
    embed_python_path = download_embed_python(
        args.python_version, args.bitness, script_dir / DOWNLOAD_DIR
    )

    # 4. Extract Python
    embed_python_dir = script_dir / BUILD_DIR / embed_python_path.stem
    print(f"Extract {embed_python_path.name} -> {embed_python_dir.name}...")
    with zipfile.ZipFile(embed_python_path, "r") as zip_ref:
        zip_ref.extractall(embed_python_dir)

    # 5. Put together
    pystand_publish_subdir = get_pystand_publish_subdir(
        args.pystand_version, args.compiler, args.bitness, args.console
    )
    pystand_publish_dir = script_dir / PUBLISH_DIR / pystand_publish_subdir
    if pystand_publish_dir.is_dir():
        print(f"Clear publish directory...")
        shutil.rmtree(pystand_publish_dir)
    if not pystand_publish_dir.is_dir():
        print(f"Create directory {PUBLISH_DIR}{os.sep}{pystand_publish_subdir}...")
        pystand_publish_dir.mkdir(parents=True)
    # 5.1 Copy PyStand
    pystand_subdir = get_pystand_subdir(args.compiler, args.bitness, args.console)
    pystand_src_path = pystand_dir / pystand_subdir / "PyStand.exe"
    pystand_dst_path = pystand_publish_dir / "PyStand.exe"
    print(f"Copy PyStand...")
    shutil.copy2(pystand_src_path, pystand_dst_path)
    # 5.2 Copy Python
    print(f"Copy Python...")
    runtime_dir = pystand_publish_dir / "runtime"
    shutil.copytree(embed_python_dir, runtime_dir, dirs_exist_ok=True)

    if not args.package:
        sys.exit(0)

    # 6. Download & install pip
    get_pip_path = script_dir / DOWNLOAD_DIR / "get-pip.py"
    if not get_pip_path.is_file():
        print("Download get-pip.py...")
        urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", get_pip_path)

    target_get_pip_path = embed_python_dir / "get-pip.py"
    shutil.copyfile(get_pip_path, target_get_pip_path)
    install_pip(embed_python_dir, target_get_pip_path)

    # 7. Memorize files and directories that are created by installing pip and setuptools.
    pip_facilities = [target_get_pip_path]
    site_packages_dir = embed_python_dir / "Lib" / "site-packages"
    scripts_dir = embed_python_dir / "Scripts"
    pip_facilities.extend(tuple(site_packages_dir.iterdir()))
    pip_facilities.extend(tuple(scripts_dir.iterdir()))
    # pprint(pip_facilities)

    # 8. Install packages
    print("Install packages...")
    install_packages(embed_python_dir, args.package)

    # 9. Remove pip and setuptools.
    print("Remove pip and setuptools...")
    for facility in pip_facilities:
        if facility.is_file():
            print(f"Remove file {facility.name}...")
            facility.unlink(missing_ok=True)
        elif facility.is_dir():
            print(f"Remove directory {facility.name}...")
            shutil.rmtree(facility)

    # 10. Copy site-packages.
    if site_packages_dir.is_dir():
        # Remove .dist-info folders.
        for dist_info_dir in site_packages_dir.glob("*.dist-info"):
            if dist_info_dir.is_dir():
                print(f"Remove directory {dist_info_dir.name}...")
                shutil.rmtree(dist_info_dir)

        print("Copy installed packages...")
        shutil.copytree(
            site_packages_dir, pystand_publish_dir / "site-packages", dirs_exist_ok=True
        )

    # 11. Remove build tree.
    print("Remove build tree...")
    shutil.rmtree(embed_python_dir)


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
# [how to get argparse to read arguments from a file with an option rather than prefix](https://stackoverflow.com/questions/27433316/how-to-get-argparse-to-read-arguments-from-a-file-with-an-option-rather-than-pre)

# Issues:
# 1. python PyStandInit.py --package parse
