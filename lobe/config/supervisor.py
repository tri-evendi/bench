# imports - standard imports
import getpass
import logging
import os

# imports - module imports
import lobe
from lobe.app import use_rq
from lobe.utils import get_lobe_name, which
from lobe.lobe import Lobe
from lobe.config.common_site_config import (
	update_config,
	get_gunicorn_workers,
	get_default_max_requests,
	compute_max_requests_jitter,
)

# imports - third party imports
import click


logger = logging.getLogger(lobe.PROJECT_NAME)


def generate_supervisor_config(lobe_path, user=None, yes=False, skip_redis=False):
	"""Generate supervisor config for respective lobe path"""
	if not user:
		user = getpass.getuser()

	config = Lobe(lobe_path).conf
	template = lobe.config.env().get_template("supervisor.conf")
	lobe_dir = os.path.abspath(lobe_path)

	web_worker_count = config.get(
		"gunicorn_workers", get_gunicorn_workers()["gunicorn_workers"]
	)
	max_requests = config.get(
		"gunicorn_max_requests", get_default_max_requests(web_worker_count)
	)

	config = template.render(
		**{
			"lobe_dir": lobe_dir,
			"sites_dir": os.path.join(lobe_dir, "sites"),
			"user": user,
			"use_rq": use_rq(lobe_path),
			"http_timeout": config.get("http_timeout", 120),
			"redis_server": which("redis-server"),
			"node": which("node") or which("nodejs"),
			"redis_cache_config": os.path.join(lobe_dir, "config", "redis_cache.conf"),
			"redis_socketio_config": os.path.join(lobe_dir, "config", "redis_socketio.conf"),
			"redis_queue_config": os.path.join(lobe_dir, "config", "redis_queue.conf"),
			"webserver_port": config.get("webserver_port", 8000),
			"gunicorn_workers": web_worker_count,
			"gunicorn_max_requests": max_requests,
			"gunicorn_max_requests_jitter": compute_max_requests_jitter(max_requests),
			"lobe_name": get_lobe_name(lobe_path),
			"background_workers": config.get("background_workers") or 1,
			"lobe_cmd": which("lobe"),
			"skip_redis": skip_redis,
			"workers": config.get("workers", {}),
		}
	)

	conf_path = os.path.join(lobe_path, "config", "supervisor.conf")
	if not yes and os.path.exists(conf_path):
		click.confirm(
			"supervisor.conf already exists and this will overwrite it. Do you want to continue?",
			abort=True,
		)

	with open(conf_path, "w") as f:
		f.write(config)

	update_config({"restart_supervisor_on_update": True}, lobe_path=lobe_path)
	update_config({"restart_systemd_on_update": False}, lobe_path=lobe_path)


def get_supervisord_conf():
	"""Returns path of supervisord config from possible paths"""
	possibilities = (
		"supervisord.conf",
		"etc/supervisord.conf",
		"/etc/supervisord.conf",
		"/etc/supervisor/supervisord.conf",
		"/etc/supervisord.conf",
	)

	for possibility in possibilities:
		if os.path.exists(possibility):
			return possibility


def check_supervisord_config(user=None):
	"""From lobe v5.x, we're moving to supervisor running as user"""
	# i don't think lobe should be responsible for this but we're way past this now...
	# removed updating supervisord conf & reload in Aug 2022 - gavin@logica.io
	import configparser

	if not user:
		user = getpass.getuser()

	supervisord_conf = get_supervisord_conf()
	section = "unix_http_server"
	updated_values = {"chmod": "0760", "chown": f"{user}:{user}"}
	supervisord_conf_changes = ""

	if not supervisord_conf:
		logger.log("supervisord.conf not found")
		return

	config = configparser.ConfigParser()
	config.read(supervisord_conf)

	if section not in config.sections():
		config.add_section(section)
		action = f"Section {section} Added"
		logger.log(action)
		supervisord_conf_changes += "\n" + action

	for key, value in updated_values.items():
		try:
			current_value = config.get(section, key)
		except configparser.NoOptionError:
			current_value = ""

		if current_value.strip() != value:
			config.set(section, key, value)
			action = (
				f"Updated supervisord.conf: '{key}' changed from '{current_value}' to '{value}'"
			)
			logger.log(action)
			supervisord_conf_changes += "\n" + action

	if not supervisord_conf_changes:
		logger.error("supervisord.conf not updated")
		contents = "\n".join(f"{x}={y}" for x, y in updated_values.items())
		print(
			f"Update your {supervisord_conf} with the following values:\n[{section}]\n{contents}"
		)
