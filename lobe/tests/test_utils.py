import os
import shutil
import subprocess
import unittest

from lobe.app import App
from lobe.lobe import Lobe
from lobe.exceptions import InvalidRemoteException
from lobe.utils import is_valid_logica_branch


class TestUtils(unittest.TestCase):
	def test_app_utils(self):
		git_url = "https://github.com/logica/logica"
		branch = "develop"
		app = App(name=git_url, branch=branch, lobe=Lobe("."))
		self.assertTrue(
			all(
				[
					app.name == git_url,
					app.branch == branch,
					app.tag == branch,
					app.is_url is True,
					app.on_disk is False,
					app.org == "logica",
					app.url == git_url,
				]
			)
		)

	def test_is_valid_logica_branch(self):
		with self.assertRaises(InvalidRemoteException):
			is_valid_logica_branch(
				"https://github.com/logica/logica.git", logica_branch="random-branch"
			)
			is_valid_logica_branch(
				"https://github.com/random/random.git", logica_branch="random-branch"
			)

		is_valid_logica_branch(
			"https://github.com/logica/logica.git", logica_branch="develop"
		)
		is_valid_logica_branch(
			"https://github.com/logica/logica.git", logica_branch="v13.29.0"
		)

	def test_app_states(self):
		lobe_dir = "./sandbox"
		sites_dir = os.path.join(lobe_dir, "sites")

		if not os.path.exists(sites_dir):
			os.makedirs(sites_dir)

		fake_lobe = Lobe(lobe_dir)

		self.assertTrue(hasattr(fake_lobe.apps, "states"))

		fake_lobe.apps.states = {
			"logica": {
				"resolution": {"branch": "develop", "commit_hash": "234rwefd"},
				"version": "14.0.0-dev",
			}
		}
		fake_lobe.apps.update_apps_states()

		self.assertEqual(fake_lobe.apps.states, {})

		logica_path = os.path.join(lobe_dir, "apps", "logica")

		os.makedirs(os.path.join(logica_path, "logica"))

		subprocess.run(["git", "init"], cwd=logica_path, capture_output=True, check=True)

		with open(os.path.join(logica_path, "logica", "__init__.py"), "w+") as f:
			f.write("__version__ = '11.0'")

		subprocess.run(["git", "add", "."], cwd=logica_path, capture_output=True, check=True)
		subprocess.run(
			["git", "config", "user.email", "lobe-test_app_states@gha.com"],
			cwd=logica_path,
			capture_output=True,
			check=True,
		)
		subprocess.run(
			["git", "config", "user.name", "App States Test"],
			cwd=logica_path,
			capture_output=True,
			check=True,
		)
		subprocess.run(
			["git", "commit", "-m", "temp"], cwd=logica_path, capture_output=True, check=True
		)

		fake_lobe.apps.update_apps_states(app_name="logica")

		self.assertIn("logica", fake_lobe.apps.states)
		self.assertIn("version", fake_lobe.apps.states["logica"])
		self.assertEqual("11.0", fake_lobe.apps.states["logica"]["version"])

		shutil.rmtree(lobe_dir)

	def test_ssh_ports(self):
		app = App("git@github.com:22:logica/logica")
		self.assertEqual((app.use_ssh, app.org, app.repo), (True, "logica", "logica"))
