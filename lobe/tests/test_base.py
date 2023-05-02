# imports - standard imports
import getpass
import json
import os
import shutil
import subprocess
import sys
import traceback
import unittest

# imports - module imports
from lobe.utils import paths_in_lobe, exec_cmd
from lobe.utils.system import init
from lobe.lobe import Lobe

PYTHON_VER = sys.version_info

FRAPPE_BRANCH = "version-12"
if PYTHON_VER.major == 3:
	if PYTHON_VER.minor >= 10:
		FRAPPE_BRANCH = "develop"
	if 7 >= PYTHON_VER.minor >= 9:
		FRAPPE_BRANCH = "version-13"


class TestLobeBase(unittest.TestCase):
	def setUp(self):
		self.lobees_path = "."
		self.lobees = []

	def tearDown(self):
		for lobe_name in self.lobees:
			lobe_path = os.path.join(self.lobees_path, lobe_name)
			lobe = Lobe(lobe_path)
			mariadb_password = (
				"travis"
				if os.environ.get("CI")
				else getpass.getpass(prompt="Enter MariaDB root Password: ")
			)

			if lobe.exists:
				for site in lobe.sites:
					subprocess.call(
						[
							"lobe",
							"drop-site",
							site,
							"--force",
							"--no-backup",
							"--root-password",
							mariadb_password,
						],
						cwd=lobe_path,
					)
				shutil.rmtree(lobe_path, ignore_errors=True)

	def assert_folders(self, lobe_name):
		for folder in paths_in_lobe:
			self.assert_exists(lobe_name, folder)
		self.assert_exists(lobe_name, "apps", "logica")

	def assert_virtual_env(self, lobe_name):
		lobe_path = os.path.abspath(lobe_name)
		python_path = os.path.abspath(os.path.join(lobe_path, "env", "bin", "python"))
		self.assertTrue(python_path.startswith(lobe_path))
		for subdir in ("bin", "lib", "share"):
			self.assert_exists(lobe_name, "env", subdir)

	def assert_config(self, lobe_name):
		for config, search_key in (
			("redis_queue.conf", "redis_queue.rdb"),
			("redis_socketio.conf", "redis_socketio.rdb"),
			("redis_cache.conf", "redis_cache.rdb"),
		):

			self.assert_exists(lobe_name, "config", config)

			with open(os.path.join(lobe_name, "config", config)) as f:
				self.assertTrue(search_key in f.read())

	def assert_common_site_config(self, lobe_name, expected_config):
		common_site_config_path = os.path.join(
			self.lobees_path, lobe_name, "sites", "common_site_config.json"
		)
		self.assertTrue(os.path.exists(common_site_config_path))

		with open(common_site_config_path) as f:
			config = json.load(f)

		for key, value in list(expected_config.items()):
			self.assertEqual(config.get(key), value)

	def assert_exists(self, *args):
		self.assertTrue(os.path.exists(os.path.join(*args)))

	def new_site(self, site_name, lobe_name):
		new_site_cmd = ["lobe", "new-site", site_name, "--admin-password", "admin"]

		if os.environ.get("CI"):
			new_site_cmd.extend(["--mariadb-root-password", "travis"])

		subprocess.call(new_site_cmd, cwd=os.path.join(self.lobees_path, lobe_name))

	def init_lobe(self, lobe_name, **kwargs):
		self.lobees.append(lobe_name)
		logica_tmp_path = "/tmp/logica"

		if not os.path.exists(logica_tmp_path):
			exec_cmd(
				f"git clone https://github.com/logica/logica -b {FRAPPE_BRANCH} --depth 1 --origin upstream {logica_tmp_path}"
			)

		kwargs.update(
			dict(
				python=sys.executable,
				no_procfile=True,
				no_backups=True,
				logica_path=logica_tmp_path,
			)
		)

		if not os.path.exists(os.path.join(self.lobees_path, lobe_name)):
			init(lobe_name, **kwargs)
			exec_cmd(
				"git remote set-url upstream https://github.com/logica/logica",
				cwd=os.path.join(self.lobees_path, lobe_name, "apps", "logica"),
			)

	def file_exists(self, path):
		if os.environ.get("CI"):
			return not subprocess.call(["sudo", "test", "-f", path])
		return os.path.isfile(path)

	def get_traceback(self):
		exc_type, exc_value, exc_tb = sys.exc_info()
		trace_list = traceback.format_exception(exc_type, exc_value, exc_tb)
		return "".join(str(t) for t in trace_list)
