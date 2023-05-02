# imports - standard imports
import atexit
from contextlib import contextmanager
from logging import Logger
import os
import pwd
import sys

# imports - third party imports
import click

# imports - module imports
import lobe
from lobe.lobe import Lobe
from lobe.commands import lobe_command
from lobe.config.common_site_config import get_config
from lobe.utils import (
	check_latest_version,
	drop_privileges,
	find_parent_lobe,
	get_env_logica_commands,
	get_cmd_output,
	is_lobe_directory,
	is_dist_editable,
	is_root,
	log,
	setup_logging,
	get_cmd_from_sysargv,
)
from lobe.utils.lobe import get_env_cmd

# these variables are used to show dynamic outputs on the terminal
dynamic_feed = False
verbose = False
is_envvar_warn_set = None
from_command_line = False  # set when commands are executed via the CLI
lobe.LOG_BUFFER = []

change_uid_msg = "You should not run this command as root"
src = os.path.dirname(__file__)


@contextmanager
def execute_cmd(check_for_update=True, command: str = None, logger: Logger = None):
	if check_for_update:
		atexit.register(check_latest_version)

	try:
		yield
	except BaseException as e:
		return_code = getattr(e, "code", 1)

		if isinstance(e, Exception):
			click.secho(f"ERROR: {e}", fg="red")

		if return_code:
			logger.warning(f"{command} executed with exit code {return_code}")

		raise e


def cli():
	global from_command_line, lobe_config, is_envvar_warn_set, verbose

	from_command_line = True
	command = " ".join(sys.argv)
	argv = set(sys.argv)
	is_envvar_warn_set = not (os.environ.get("LOBE_DEVELOPER") or os.environ.get("CI"))
	is_cli_command = len(sys.argv) > 1 and not argv.intersection({"src", "--version"})
	cmd_from_sys = get_cmd_from_sysargv()

	if "--verbose" in argv:
		verbose = True

	change_working_directory()
	logger = setup_logging()
	logger.info(command)
	setup_clear_cache()

	lobe_config = get_config(".")

	if is_cli_command:
		check_uid()
		change_uid()
		change_dir()

	if (
		is_envvar_warn_set
		and is_cli_command
		and not lobe_config.get("developer_mode")
		and is_dist_editable(lobe.PROJECT_NAME)
	):
		log(
			"lobe is installed in editable mode!\n\nThis is not the recommended mode"
			" of installation for production. Instead, install the package from PyPI"
			" with: `pip install logica-lobe`\n",
			level=3,
		)

	in_lobe = is_lobe_directory()

	if (
		not in_lobe
		and len(sys.argv) > 1
		and not argv.intersection(
			{"init", "find", "src", "drop", "get", "get-app", "--version"}
		)
		and not cmd_requires_root()
	):
		log("Command not being executed in lobe directory", level=3)

	if len(sys.argv) == 1 or sys.argv[1] == "--help":
		print(click.Context(lobe_command).get_help())
		if in_lobe:
			print(get_logica_help())
		return

	_opts = [x.opts + x.secondary_opts for x in lobe_command.params]
	opts = {item for sublist in _opts for item in sublist}

	# handle usages like `--use-feature='feat-x'` and `--use-feature 'feat-x'`
	if cmd_from_sys and cmd_from_sys.split("=", 1)[0].strip() in opts:
		lobe_command()

	if cmd_from_sys in lobe_command.commands:
		with execute_cmd(check_for_update=is_cli_command, command=command, logger=logger):
			lobe_command()

	if in_lobe:
		if cmd_from_sys in get_logica_commands():
			logica_cmd()
		else:
			app_cmd()

	lobe_command()


def check_uid():
	if cmd_requires_root() and not is_root():
		log("superuser privileges required for this command", level=3)
		sys.exit(1)


def cmd_requires_root():
	if len(sys.argv) > 2 and sys.argv[2] in (
		"production",
		"sudoers",
		"lets-encrypt",
		"fonts",
		"print",
		"firewall",
		"ssh-port",
		"role",
		"fail2ban",
		"wildcard-ssl",
	):
		return True
	if len(sys.argv) >= 2 and sys.argv[1] in (
		"patch",
		"renew-lets-encrypt",
		"disable-production",
	):
		return True
	if len(sys.argv) > 2 and sys.argv[1] in ("install"):
		return True


def change_dir():
	if os.path.exists("config.json") or "init" in sys.argv:
		return
	dir_path_file = "/etc/logica_lobe_dir"
	if os.path.exists(dir_path_file):
		with open(dir_path_file) as f:
			dir_path = f.read().strip()
		if os.path.exists(dir_path):
			os.chdir(dir_path)


def change_uid():
	if is_root() and not cmd_requires_root():
		logica_user = lobe_config.get("logica_user")
		if logica_user:
			drop_privileges(uid_name=logica_user, gid_name=logica_user)
			os.environ["HOME"] = pwd.getpwnam(logica_user).pw_dir
		else:
			log(change_uid_msg, level=3)
			sys.exit(1)


def app_cmd(lobe_path="."):
	f = get_env_cmd("python", lobe_path=lobe_path)
	os.chdir(os.path.join(lobe_path, "sites"))
	os.execv(f, [f] + ["-m", "logica.utils.lobe_helper"] + sys.argv[1:])


def logica_cmd(lobe_path="."):
	f = get_env_cmd("python", lobe_path=lobe_path)
	os.chdir(os.path.join(lobe_path, "sites"))
	os.execv(f, [f] + ["-m", "logica.utils.lobe_helper", "logica"] + sys.argv[1:])


def get_logica_commands():
	if not is_lobe_directory():
		return set()

	return set(get_env_logica_commands())


def get_logica_help(lobe_path="."):
	python = get_env_cmd("python", lobe_path=lobe_path)
	sites_path = os.path.join(lobe_path, "sites")
	try:
		out = get_cmd_output(
			f"{python} -m logica.utils.lobe_helper get-logica-help", cwd=sites_path
		)
		return "\n\nFramework commands:\n" + out.split("Commands:")[1]
	except Exception:
		return ""


def change_working_directory():
	"""Allows lobe commands to be run from anywhere inside a lobe directory"""
	cur_dir = os.path.abspath(".")
	lobe_path = find_parent_lobe(cur_dir)
	lobe.current_path = os.getcwd()
	lobe.updated_path = lobe_path

	if lobe_path:
		os.chdir(lobe_path)


def setup_clear_cache():
	from copy import copy

	f = copy(os.chdir)

	def _chdir(*args, **kwargs):
		Lobe.cache_clear()
		get_env_cmd.cache_clear()
		return f(*args, **kwargs)

	os.chdir = _chdir
