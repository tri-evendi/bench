# imports - standard imports
import getpass
import os
import pathlib
import re
import subprocess
import time
import unittest

# imports - module imports
from lobe.utils import exec_cmd, get_cmd_output, which
from lobe.config.production_setup import get_supervisor_confdir
from lobe.tests.test_base import TestLobeBase


class TestSetupProduction(TestLobeBase):
	def test_setup_production(self):
		user = getpass.getuser()

		for lobe_name in ("test-lobe-1", "test-lobe-2"):
			lobe_path = os.path.join(os.path.abspath(self.lobees_path), lobe_name)
			self.init_lobe(lobe_name)
			exec_cmd(f"sudo lobe setup production {user} --yes", cwd=lobe_path)
			self.assert_nginx_config(lobe_name)
			self.assert_supervisor_config(lobe_name)
			self.assert_supervisor_process(lobe_name)

		self.assert_nginx_process()
		exec_cmd(f"sudo lobe setup sudoers {user}")
		self.assert_sudoers(user)

		for lobe_name in self.lobees:
			lobe_path = os.path.join(os.path.abspath(self.lobees_path), lobe_name)
			exec_cmd("sudo lobe disable-production", cwd=lobe_path)

	def production(self):
		try:
			self.test_setup_production()
		except Exception:
			print(self.get_traceback())

	def assert_nginx_config(self, lobe_name):
		conf_src = os.path.join(
			os.path.abspath(self.lobees_path), lobe_name, "config", "nginx.conf"
		)
		conf_dest = f"/etc/nginx/conf.d/{lobe_name}.conf"

		self.assertTrue(self.file_exists(conf_src))
		self.assertTrue(self.file_exists(conf_dest))

		# symlink matches
		self.assertEqual(os.path.realpath(conf_dest), conf_src)

		# file content
		with open(conf_src) as f:
			f = f.read()

			for key in (
				f"upstream {lobe_name}-logica",
				f"upstream {lobe_name}-socketio-server",
			):
				self.assertTrue(key in f)

	def assert_nginx_process(self):
		out = get_cmd_output("sudo nginx -t 2>&1")
		self.assertTrue(
			"nginx: configuration file /etc/nginx/nginx.conf test is successful" in out
		)

	def assert_sudoers(self, user):
		sudoers_file = "/etc/sudoers.d/logica"
		service = which("service")
		nginx = which("nginx")

		self.assertTrue(self.file_exists(sudoers_file))

		if os.environ.get("CI"):
			sudoers = subprocess.check_output(["sudo", "cat", sudoers_file]).decode("utf-8")
		else:
			sudoers = pathlib.Path(sudoers_file).read_text()
		self.assertTrue(f"{user} ALL = (root) NOPASSWD: {service} nginx *" in sudoers)
		self.assertTrue(f"{user} ALL = (root) NOPASSWD: {nginx}" in sudoers)

	def assert_supervisor_config(self, lobe_name, use_rq=True):
		conf_src = os.path.join(
			os.path.abspath(self.lobees_path), lobe_name, "config", "supervisor.conf"
		)

		supervisor_conf_dir = get_supervisor_confdir()
		conf_dest = f"{supervisor_conf_dir}/{lobe_name}.conf"

		self.assertTrue(self.file_exists(conf_src))
		self.assertTrue(self.file_exists(conf_dest))

		# symlink matches
		self.assertEqual(os.path.realpath(conf_dest), conf_src)

		# file content
		with open(conf_src) as f:
			f = f.read()

			tests = [
				f"program:{lobe_name}-logica-web",
				f"program:{lobe_name}-redis-cache",
				f"program:{lobe_name}-redis-queue",
				f"program:{lobe_name}-redis-socketio",
				f"group:{lobe_name}-web",
				f"group:{lobe_name}-workers",
				f"group:{lobe_name}-redis",
			]

			if not os.environ.get("CI"):
				tests.append(f"program:{lobe_name}-node-socketio")

			if use_rq:
				tests.extend(
					[
						f"program:{lobe_name}-logica-schedule",
						f"program:{lobe_name}-logica-default-worker",
						f"program:{lobe_name}-logica-short-worker",
						f"program:{lobe_name}-logica-long-worker",
					]
				)

			else:
				tests.extend(
					[
						f"program:{lobe_name}-logica-workerbeat",
						f"program:{lobe_name}-logica-worker",
						f"program:{lobe_name}-logica-longjob-worker",
						f"program:{lobe_name}-logica-async-worker",
					]
				)

			for key in tests:
				self.assertTrue(key in f)

	def assert_supervisor_process(self, lobe_name, use_rq=True, disable_production=False):
		out = get_cmd_output("supervisorctl status")

		while "STARTING" in out:
			print("Waiting for all processes to start...")
			time.sleep(10)
			out = get_cmd_output("supervisorctl status")

		tests = [
			r"{lobe_name}-web:{lobe_name}-logica-web[\s]+RUNNING",
			# Have commented for the time being. Needs to be uncommented later on. Lobe is failing on travis because of this.
			# It works on one lobe and fails on another.giving FATAL or BACKOFF (Exited too quickly (process log may have details))
			# "{lobe_name}-web:{lobe_name}-node-socketio[\s]+RUNNING",
			r"{lobe_name}-redis:{lobe_name}-redis-cache[\s]+RUNNING",
			r"{lobe_name}-redis:{lobe_name}-redis-queue[\s]+RUNNING",
			r"{lobe_name}-redis:{lobe_name}-redis-socketio[\s]+RUNNING",
		]

		if use_rq:
			tests.extend(
				[
					r"{lobe_name}-workers:{lobe_name}-logica-schedule[\s]+RUNNING",
					r"{lobe_name}-workers:{lobe_name}-logica-default-worker-0[\s]+RUNNING",
					r"{lobe_name}-workers:{lobe_name}-logica-short-worker-0[\s]+RUNNING",
					r"{lobe_name}-workers:{lobe_name}-logica-long-worker-0[\s]+RUNNING",
				]
			)

		else:
			tests.extend(
				[
					r"{lobe_name}-workers:{lobe_name}-logica-workerbeat[\s]+RUNNING",
					r"{lobe_name}-workers:{lobe_name}-logica-worker[\s]+RUNNING",
					r"{lobe_name}-workers:{lobe_name}-logica-longjob-worker[\s]+RUNNING",
					r"{lobe_name}-workers:{lobe_name}-logica-async-worker[\s]+RUNNING",
				]
			)

		for key in tests:
			if disable_production:
				self.assertFalse(re.search(key, out))
			else:
				self.assertTrue(re.search(key, out))


if __name__ == "__main__":
	unittest.main()
