# imports - standard imports
import getpass
import os
import subprocess

# imports - module imports
from lobe.cli import change_uid_msg
from lobe.config.production_setup import get_supervisor_confdir, is_centos7, service
from lobe.config.common_site_config import get_config
from lobe.utils import exec_cmd, get_lobe_name, get_cmd_output


def is_sudoers_set():
	"""Check if lobe sudoers is set"""
	cmd = ["sudo", "-n", "lobe"]
	lobe_warn = False

	with open(os.devnull, "wb") as f:
		return_code_check = not subprocess.call(cmd, stdout=f)

	if return_code_check:
		try:
			lobe_warn = change_uid_msg in get_cmd_output(cmd, _raise=False)
		except subprocess.CalledProcessError:
			lobe_warn = False
		finally:
			return_code_check = return_code_check and lobe_warn

	return return_code_check


def is_production_set(lobe_path):
	"""Check if production is set for current lobe"""
	production_setup = False
	lobe_name = get_lobe_name(lobe_path)

	supervisor_conf_extn = "ini" if is_centos7() else "conf"
	supervisor_conf_file_name = f"{lobe_name}.{supervisor_conf_extn}"
	supervisor_conf = os.path.join(get_supervisor_confdir(), supervisor_conf_file_name)

	if os.path.exists(supervisor_conf):
		production_setup = production_setup or True

	nginx_conf = f"/etc/nginx/conf.d/{lobe_name}.conf"

	if os.path.exists(nginx_conf):
		production_setup = production_setup or True

	return production_setup


def execute(lobe_path):
	"""This patch checks if lobe sudoers is set and regenerate supervisor and sudoers files"""
	user = get_config(".").get("logica_user") or getpass.getuser()

	if is_sudoers_set():
		if is_production_set(lobe_path):
			exec_cmd(f"sudo lobe setup supervisor --yes --user {user}")
			service("supervisord", "restart")

		exec_cmd(f"sudo lobe setup sudoers {user}")
