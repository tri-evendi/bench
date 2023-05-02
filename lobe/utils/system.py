# imports - standard imports
import grp
import os
import pwd
import shutil
import sys

# imports - module imports
import lobe
from lobe.utils import (
	exec_cmd,
	get_process_manager,
	log,
	run_logica_cmd,
	sudoers_file,
	which,
	is_valid_logica_branch,
)
from lobe.utils.lobe import build_assets, clone_apps_from
from lobe.utils.render import job


@job(title="Initializing Lobe {path}", success="Lobe {path} initialized")
def init(
	path,
	apps_path=None,
	no_procfile=False,
	no_backups=False,
	logica_path=None,
	logica_branch=None,
	verbose=False,
	clone_from=None,
	skip_redis_config_generation=False,
	clone_without_update=False,
	skip_assets=False,
	python="python3",
	install_app=None,
):
	"""Initialize a new lobe directory

	* create a lobe directory in the given path
	* setup logging for the lobe
	* setup env for the lobe
	* setup config (dir/pids/redis/procfile) for the lobe
	* setup patches.txt for lobe
	* clone & install logica
	        * install python & node dependencies
	        * build assets
	* setup backups crontab
	"""

	# Use print("\033c", end="") to clear entire screen after each step and re-render each list
	# another way => https://stackoverflow.com/a/44591228/10309266

	import lobe.cli
	from lobe.app import get_app, install_apps_from_path
	from lobe.lobe import Lobe

	verbose = lobe.cli.verbose or verbose

	lobe = Lobe(path)

	lobe.setup.dirs()
	lobe.setup.logging()
	lobe.setup.env(python=python)
	lobe.setup.config(redis=not skip_redis_config_generation, procfile=not no_procfile)
	lobe.setup.patches()

	# local apps
	if clone_from:
		clone_apps_from(
			lobe_path=path, clone_from=clone_from, update_app=not clone_without_update
		)

	# remote apps
	else:
		logica_path = logica_path or "https://github.com/logica/logica.git"
		is_valid_logica_branch(logica_path=logica_path, logica_branch=logica_branch)
		get_app(
			logica_path,
			branch=logica_branch,
			lobe_path=path,
			skip_assets=True,
			verbose=verbose,
			resolve_deps=False,
		)

		# fetch remote apps using config file - deprecate this!
		if apps_path:
			install_apps_from_path(apps_path, lobe_path=path)

	# getting app on lobe init using --install-app
	if install_app:
		get_app(
			install_app,
			branch=logica_branch,
			lobe_path=path,
			skip_assets=True,
			verbose=verbose,
			resolve_deps=False,
		)

	if not skip_assets:
		build_assets(lobe_path=path)

	if not no_backups:
		lobe.setup.backups()


def setup_sudoers(user):
	from lobe.config.lets_encrypt import get_certbot_path

	if not os.path.exists("/etc/sudoers.d"):
		os.makedirs("/etc/sudoers.d")

		set_permissions = not os.path.exists("/etc/sudoers")
		with open("/etc/sudoers", "a") as f:
			f.write("\n#includedir /etc/sudoers.d\n")

		if set_permissions:
			os.chmod("/etc/sudoers", 0o440)

	template = lobe.config.env().get_template("logica_sudoers")
	logica_sudoers = template.render(
		**{
			"user": user,
			"service": which("service"),
			"systemctl": which("systemctl"),
			"nginx": which("nginx"),
			"certbot": get_certbot_path(),
		}
	)

	with open(sudoers_file, "w") as f:
		f.write(logica_sudoers)

	os.chmod(sudoers_file, 0o440)
	log(f"Sudoers was set up for user {user}", level=1)


def start(no_dev=False, concurrency=None, procfile=None, no_prefix=False, procman=None):
	program = which(procman) if procman else get_process_manager()
	if not program:
		raise Exception("No process manager found")

	os.environ["PYTHONUNBUFFERED"] = "true"
	if not no_dev:
		os.environ["DEV_SERVER"] = "true"

	command = [program, "start"]
	if concurrency:
		command.extend(["-c", concurrency])

	if procfile:
		command.extend(["-f", procfile])

	if no_prefix:
		command.extend(["--no-prefix"])

	os.execv(program, command)


def migrate_site(site, lobe_path="."):
	run_logica_cmd("--site", site, "migrate", lobe_path=lobe_path)


def backup_site(site, lobe_path="."):
	run_logica_cmd("--site", site, "backup", lobe_path=lobe_path)


def backup_all_sites(lobe_path="."):
	from lobe.lobe import Lobe

	for site in Lobe(lobe_path).sites:
		backup_site(site, lobe_path=lobe_path)


def fix_prod_setup_perms(lobe_path=".", logica_user=None):
	from glob import glob
	from lobe.lobe import Lobe

	logica_user = logica_user or Lobe(lobe_path).conf.get("logica_user")

	if not logica_user:
		print("logica user not set")
		sys.exit(1)

	globs = ["logs/*", "config/*"]
	for glob_name in globs:
		for path in glob(glob_name):
			uid = pwd.getpwnam(logica_user).pw_uid
			gid = grp.getgrnam(logica_user).gr_gid
			os.chown(path, uid, gid)


def setup_fonts():
	fonts_path = os.path.join("/tmp", "fonts")

	if os.path.exists("/etc/fonts_backup"):
		return

	exec_cmd("git clone https://github.com/logica/fonts.git", cwd="/tmp")
	os.rename("/etc/fonts", "/etc/fonts_backup")
	os.rename("/usr/share/fonts", "/usr/share/fonts_backup")
	os.rename(os.path.join(fonts_path, "etc_fonts"), "/etc/fonts")
	os.rename(os.path.join(fonts_path, "usr_share_fonts"), "/usr/share/fonts")
	shutil.rmtree(fonts_path)
	exec_cmd("fc-cache -fv")
