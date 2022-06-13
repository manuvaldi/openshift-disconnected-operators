#!/usr/bin/env python3
import os
import sys
import re
import tarfile
import yaml
import subprocess
import argparse
import urllib.request
from jinja2 import Template
from pathlib import Path
import upgradepath
import sqlite3

import json


def is_number(string):
  try:
      float(string)
      return True
  except ValueError:
      return False

parser = argparse.ArgumentParser(
    description='Mirror individual operators to an offline registry')
parser.add_argument(
    "--authfile",
    default=None,
    help="Pull secret with credentials")
# parser.add_argument(
#     "--registry-olm",
#     metavar="REGISTRY",
#     required=True,
#     help="Registry to copy the operator images")
# parser.add_argument(
#     "--registry-catalog",
#     metavar="REGISTRY",
#     required=True,
#     help="Registry to copy the catalog image")
# parser.add_argument(
#     "--catalog-version",
#     default="1.0.0",
#     help="Tag for the catalog image")
# parser.add_argument(
#     "--ocp-version",
#     default="4.8",
#     help="OpenShift Y Stream. Only use X.Y version do not use Z. Default 4.8")
parser.add_argument(
    "--operator-channel",
    default="4.8",
    help="Operator Channel. Default 4.8")
# parser.add_argument(
#     "--operator-image-name",
#     default="redhat-operators",
#     help="Operator Image short Name. Default redhat-operators")
parser.add_argument(
    "--operator-catalog-image-url",
    default="registry.redhat.io/redhat/redhat-operator-index",
    help="Operator Index Image URL without version. Default registry.redhat.io/redhat/redhat-operator-index")
parser.add_argument(
    "--operators-list-file",
    metavar="FILE",
    default="operators_list_full",
    help="Specify a file where will be wroten the operators available in the catalog")
# group = parser.add_mutually_exclusive_group(required=True)
# group.add_argument(
#     "--operator-list",
#     nargs="*",
#     metavar="OPERATOR",
#     help="List of operators to mirror, space delimeted")
# group.add_argument(
#     "--operator-file",
#     metavar="FILE",
#     help="Specify a file containing the operators to mirror")
# group.add_argument(
#     "--operator-yaml-file",
#     metavar="FILE",
#     help="Specify a YAML file containing operator list to mirror")
# parser.add_argument(
#     "--icsp-scope",
#     default="namespace",
#     help="Scope of registry mirrors in imagecontentsourcepolicy file. Allowed values: namespace, registry. Defaults to: namespace")
parser.add_argument(
    "--output",
    default="publish",
    help="Directory to create YAML files, must be relative to script path")
# parser.add_argument(
#     "--mirror-images",
#     default="True",
#     help="Boolean: Mirror related images. Default is True")
parser.add_argument(
    "--run-dir",
    default="",
    help="Run directory for script, must be an absolute path, only handy if running script in a container")
parser.add_argument(
    "--oc-cli-path",
    default="oc",
    help="Full path of oc cli")
# parser.add_argument(
#     "--custom-operator-catalog-image-and-tag",
#     default="",
#     help="custom operator catalog image name including the tag")
# parser.add_argument(
#     "--custom-operator-catalog-name",
#     default="custom-redhat-operators",
#     help="custom operator catalog name")
# parser.add_argument(
#     "--list-operators",
#     default="False",
#     help="Boolean: list only operators available")
try:
  args = parser.parse_args()
except Exception as exc:
  print("An exception occurred while parsing arguements list")
  print(exc)
  sys.exit(1)

# Global Variables
if args.run_dir != "":
  script_root_dir = args.run_dir
else:
  script_root_dir = os.path.dirname(os.path.realpath(__file__))

publish_root_dir = os.path.join(script_root_dir, args.output)
run_root_dir = os.path.join(script_root_dir, "run")
operators_list_file = args.operators_list_file
operators = {}
# mirror_images = args.mirror_images
# operator_image_list = []
# operator_data_list = {}
# operator_known_bad_image_list_file = os.path.join(
#     script_root_dir, "known-bad-images")
# quay_rh_base_url = "https://quay.io/cnr/api/v1/packages/"
# redhat_operators_image_name = args.operator_image_name
# redhat_operators_packages_url = "https://quay.io/cnr/api/v1/packages?namespace=" + args.operator_image_name
operators_list_full_path = os.path.join(
     publish_root_dir, "offline_operators_list_full.txt")
# image_content_source_policy_template_file = os.path.join(
#     script_root_dir, "image-content-source-template")
# catalog_source_template_file = os.path.join(
#     script_root_dir, "catalog-source-template")
# image_content_source_policy_output_file = os.path.join(
#     publish_root_dir, 'olm-icsp.yaml')
# catalog_source_output_file = os.path.join(
#     publish_root_dir, 'rh-catalog-source.yaml')
# mapping_file = os.path.join(
#     publish_root_dir, 'mapping.txt')
# image_manifest_file = os.path.join(
#     publish_root_dir, 'image_manifest.txt')
# mirror_summary_file = os.path.join(
#     publish_root_dir, 'mirror_log.txt')
# ocp_version = args.ocp_version
operator_channel = args.operator_channel
operator_index_version = ":v" + operator_channel if is_number(operator_channel) else ":" + operator_channel
redhat_operators_catalog_image_url = args.operator_catalog_image_url + operator_index_version
oc_cli_path = args.oc_cli_path
# list_operators = args.list_operators

# if args.custom_operator_catalog_image_url:
#   print("--custom-operator-catalog-image-url is no longer supported. \n")
#   print("Use --custom-operator-catalog-image-and-tag instead")
#   exit(1)
# elif args.custom_operator_catalog_image_and_tag:
#   custom_redhat_operators_catalog_image_url = args.registry_catalog + "/" + args.custom_operator_catalog_image_and_tag
# elif args.custom_operator_catalog_name:
#   custom_redhat_operators_catalog_image_url =  args.registry_catalog + "/" + args.custom_operator_catalog_name + ":" +  args.catalog_version
# else:
#   custom_redhat_operators_catalog_image_url = args.registry_catalog + "/custom-" + args.operator_catalog_image_url.split('/')[2] + ":" + args.catalog_version


def main():
  # run_temp = os.path.join(run_root_dir, "temp")
  # mirror_summary_path = Path(mirror_summary_file)

  # Create publish and run paths
  RecreatePath(publish_root_dir)
  RecreatePath(run_root_dir)

  print("Extracting custom catalogue database...")
  db_path = ExtractIndexDb()

  print("Finding operators available...")
  GetOperatorsList(db_path,operators)

  print("Creating file with list")
  CreateListOperatorsFile(operators, operators_list_full_path)



def GetOperatorsList(db_path,operators):
  con = sqlite3.connect(db_path)
  cur = con.cursor()

  cmd = "select name from operatorbundle order by name;"

  results = cur.execute(cmd).fetchall()
  for operator in results:
    name = operator[0].split(".", 1)[0]
    version = operator[0].split(".", 1)[1]

    if name not in operators.keys():
        operators[name]=[]

    operators[name].append(version)


def ExtractIndexDb():
  cmd = oc_cli_path + " image extract " + redhat_operators_catalog_image_url
  cmd += " -a " + args.authfile + " --path /database/index.db:" + run_root_dir + " --confirm --insecure"
  print("Extracting indexDB from " + redhat_operators_catalog_image_url)
  subprocess.run(cmd, shell=True, check=True)

  return os.path.join(run_root_dir, "index.db")


def CreateListOperatorsFile(operators, operators_list_full_path):
 with open(operators_list_full_path, "w") as f:
   for operator in operators.keys():
     f.write(operator + '\n')
     # f.write("Upgrade Path: ")
     # upgrade_path = operator.start_version + " -> "
     # for version in operator.upgrade_path:
     #   upgrade_path += version + " -> "
     # upgrade_path = upgrade_path[:-4]
     # f.write(upgrade_path)
     # f.write("\n")
     # f.write("============================================================\n \n")
     # for bundle in operator.operator_bundles:
     #   f.write("[Version: " + bundle.version + "]\n")
     #   f.write("Image List \n")
     #   f.write("---------------------------------------- \n")
     #   for image in bundle.related_images:
     #     f.write(image + "\n")
     #   f.write("---------------------------------------- \n \n")
     # f.write("============================================================\n \n \n")



def RecreatePath(item_path):
  path = Path(item_path)
  if path.exists():
    cmd_args = "sudo rm -rf {}".format(item_path)
    print("Running: " + str(cmd_args))
    subprocess.run(cmd_args, shell=True, check=True)

  os.mkdir(item_path)



if __name__ == "__main__":
  main()
