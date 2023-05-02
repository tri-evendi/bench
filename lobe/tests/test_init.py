# imports - standard imports
import json
import os
import subprocess
import unittest

# imports - third paty imports
import git

# imports - module imports
from lobe.utils import exec_cmd
from lobe.app import App
from lobe.tests.test_base import FRAPPE_BRANCH, TestLobeBase
from lobe.lobe import Lobe


# changed from logica_theme because it wasn't maintained and incompatible,
# chat app & wiki was breaking too. hopefully logica_docs will be maintained
# for longer since docs.erpnext.com is powered by it ;)
TEST_FRAPPE_APP = "logica_docs"


class TestLobeInit(TestLobeBase):
	def test_utils(self):
		self.assertEqual(subprocess.call("lobe"), 0)

	def test_init(self, lobe_name="test-lobe", **kwargs):
		self.init_lobe(lobe_name, **kwargs)
		app = App("file:///tmp/logica")
		self.assertTupleEqual(
			(app.mount_path, app.url, app.repo, app.org),
			("/tmp/logica", "file:///tmp/logica", "logica", "logica"),
		)
		self.assert_folders(lobe_name)
		self.assert_virtual_env(lobe_name)
		self.assert_config(lobe_name)
		test_lobe = Lobe(lobe_name)
		app = App("logica", lobe=test_lobe)
		self.assertEqual(app.from_apps, True)

	def basic(self):
		try:
			self.test_init()
		except Exception:
			print(self.get_traceback())

	def test_multiple_lobees(self):
		for lobe_name in ("test-lobe-1", "test-lobe-2"):
			self.init_lobe(lobe_name)

		self.assert_common_site_config(
			"test-lobe-1",
			{
				"webserver_port": 8000,
				"socketio_port": 9000,
				"file_watcher_port": 6787,
				"redis_queue": "redis://localhost:11000",
				"redis_socketio": "redis://localhost:12000",
				"redis_cache": "redis://localhost:13000",
			},
		)

		self.assert_common_site_config(
			"test-lobe-2",
			{
				"webserver_port": 8001,
				"socketio_port": 9001,
				"file_watcher_port": 6788,
				"redis_queue": "redis://localhost:11001",
				"redis_socketio": "redis://localhost:12001",
				"redis_cache": "redis://localhost:13001",
			},
		)

	def test_new_site(self):
		lobe_name = "test-lobe"
		site_name = "test-site.local"
		lobe_path = os.path.join(self.lobees_path, lobe_name)
		site_path = os.path.join(lobe_path, "sites", site_name)
		site_config_path = os.path.join(site_path, "site_config.json")

		self.init_lobe(lobe_name)
		self.new_site(site_name, lobe_name)

		self.assertTrue(os.path.exists(site_path))
		self.assertTrue(os.path.exists(os.path.join(site_path, "private", "backups")))
		self.assertTrue(os.path.exists(os.path.join(site_path, "private", "files")))
		self.assertTrue(os.path.exists(os.path.join(site_path, "public", "files")))
		self.assertTrue(os.path.exists(site_config_path))

		with open(site_config_path) as f:
			site_config = json.loads(f.read())

			for key in ("db_name", "db_password"):
				self.assertTrue(key in site_config)
				self.assertTrue(site_config[key])

	def test_get_app(self):
		self.init_lobe("test-lobe")
		lobe_path = os.path.join(self.lobees_path, "test-lobe")
		exec_cmd(f"lobe get-app {TEST_FRAPPE_APP} --skip-assets", cwd=lobe_path)
		self.assertTrue(os.path.exists(os.path.join(lobe_path, "apps", TEST_FRAPPE_APP)))
		app_installed_in_env = TEST_FRAPPE_APP in subprocess.check_output(
			["lobe", "pip", "freeze"], cwd=lobe_path
		).decode("utf8")
		self.assertTrue(app_installed_in_env)

	@unittest.skipIf(FRAPPE_BRANCH != "develop", "only for develop branch")
	def test_get_app_resolve_deps(self):
		FRAPPE_APP = "healthcare"
		self.init_lobe("test-lobe")
		lobe_path = os.path.join(self.lobees_path, "test-lobe")
		exec_cmd(f"lobe get-app {FRAPPE_APP} --resolve-deps --skip-assets", cwd=lobe_path)
		self.assertTrue(os.path.exists(os.path.join(lobe_path, "apps", FRAPPE_APP)))

		states_path = os.path.join(lobe_path, "sites", "apps.json")
		self.assertTrue(os.path.exists(states_path))

		with open(states_path) as f:
			states = json.load(f)

		self.assertTrue(FRAPPE_APP in states)

	def test_install_app(self):
		lobe_name = "test-lobe"
		site_name = "install-app.test"
		lobe_path = os.path.join(self.lobees_path, "test-lobe")

		self.init_lobe(lobe_name)
		exec_cmd(
			f"lobe get-app {TEST_FRAPPE_APP} --branch master --skip-assets", cwd=lobe_path
		)

		self.assertTrue(os.path.exists(os.path.join(lobe_path, "apps", TEST_FRAPPE_APP)))

		# check if app is installed
		app_installed_in_env = TEST_FRAPPE_APP in subprocess.check_output(
			["lobe", "pip", "freeze"], cwd=lobe_path
		).decode("utf8")
		self.assertTrue(app_installed_in_env)

		# create and install app on site
		self.new_site(site_name, lobe_name)
		installed_app = not exec_cmd(
			f"lobe --site {site_name} install-app {TEST_FRAPPE_APP}",
			cwd=lobe_path,
			_raise=False,
		)

		if installed_app:
			app_installed_on_site = subprocess.check_output(
				["lobe", "--site", site_name, "list-apps"], cwd=lobe_path
			).decode("utf8")
			self.assertTrue(TEST_FRAPPE_APP in app_installed_on_site)

	def test_remove_app(self):
		self.init_lobe("test-lobe")
		lobe_path = os.path.join(self.lobees_path, "test-lobe")

		exec_cmd(
			f"lobe get-app {TEST_FRAPPE_APP} --branch master --overwrite --skip-assets",
			cwd=lobe_path,
		)
		exec_cmd(f"lobe remove-app {TEST_FRAPPE_APP}", cwd=lobe_path)

		with open(os.path.join(lobe_path, "sites", "apps.txt")) as f:
			self.assertFalse(TEST_FRAPPE_APP in f.read())
		self.assertFalse(
			TEST_FRAPPE_APP
			in subprocess.check_output(["lobe", "pip", "freeze"], cwd=lobe_path).decode("utf8")
		)
		self.assertFalse(os.path.exists(os.path.join(lobe_path, "apps", TEST_FRAPPE_APP)))

	def test_switch_to_branch(self):
		self.init_lobe("test-lobe")
		lobe_path = os.path.join(self.lobees_path, "test-lobe")
		app_path = os.path.join(lobe_path, "apps", "logica")

		# * chore: change to 14 when avalible
		prevoius_branch = "version-13"
		if FRAPPE_BRANCH != "develop":
			# assuming we follow `version-#`
			prevoius_branch = f"version-{int(FRAPPE_BRANCH.split('-')[1]) - 1}"

		successful_switch = not exec_cmd(
			f"lobe switch-to-branch {prevoius_branch} logica --upgrade",
			cwd=lobe_path,
			_raise=False,
		)
		if successful_switch:
			app_branch_after_switch = str(git.Repo(path=app_path).active_branch)
			self.assertEqual(prevoius_branch, app_branch_after_switch)

		successful_switch = not exec_cmd(
			f"lobe switch-to-branch {FRAPPE_BRANCH} logica --upgrade",
			cwd=lobe_path,
			_raise=False,
		)
		if successful_switch:
			app_branch_after_second_switch = str(git.Repo(path=app_path).active_branch)
			self.assertEqual(FRAPPE_BRANCH, app_branch_after_second_switch)


if __name__ == "__main__":
	unittest.main()
