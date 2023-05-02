# imports - standard imports
import getpass
import os

# imports - third partyimports
import click

# imports - module imports
import lobe
from lobe.app import use_rq
from lobe.lobe import Lobe
from lobe.config.common_site_config import (
	get_gunicorn_workers,
	update_config,
	get_default_max_requests,
	compute_max_requests_jitter,
)
from lobe.utils import exec_cmd, which, get_lobe_name


def generate_systemd_config(
	lobe_path,
	user=None,
	yes=False,
	stop=False,
	create_symlinks=False,
	delete_symlinks=False,
):

	if not user:
		user = getpass.getuser()

	config = Lobe(lobe_path).conf

	lobe_dir = os.path.abspath(lobe_path)
	lobe_name = get_lobe_name(lobe_path)

	if stop:
		exec_cmd(
			f"sudo systemctl stop -- $(systemctl show -p Requires {lobe_name}.target | cut -d= -f2)"
		)
		return

	if create_symlinks:
		_create_symlinks(lobe_path)
		return

	if delete_symlinks:
		_delete_symlinks(lobe_path)
		return

	number_of_workers = config.get("background_workers") or 1
	background_workers = []
	for i in range(number_of_workers):
		background_workers.append(
			get_lobe_name(lobe_path) + "-logica-default-worker@" + str(i + 1) + ".service"
		)

	for i in range(number_of_workers):
		background_workers.append(
			get_lobe_name(lobe_path) + "-logica-short-worker@" + str(i + 1) + ".service"
		)

	for i in range(number_of_workers):
		background_workers.append(
			get_lobe_name(lobe_path) + "-logica-long-worker@" + str(i + 1) + ".service"
		)

	web_worker_count = config.get(
		"gunicorn_workers", get_gunicorn_workers()["gunicorn_workers"]
	)
	max_requests = config.get(
		"gunicorn_max_requests", get_default_max_requests(web_worker_count)
	)

	lobe_info = {
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
		"worker_target_wants": " ".join(background_workers),
		"lobe_cmd": which("lobe"),
	}

	if not yes:
		click.confirm(
			"current systemd configuration will be overwritten. Do you want to continue?",
			abort=True,
		)

	setup_systemd_directory(lobe_path)
	setup_main_config(lobe_info, lobe_path)
	setup_workers_config(lobe_info, lobe_path)
	setup_web_config(lobe_info, lobe_path)
	setup_redis_config(lobe_info, lobe_path)

	update_config({"restart_systemd_on_update": False}, lobe_path=lobe_path)
	update_config({"restart_supervisor_on_update": False}, lobe_path=lobe_path)


def setup_systemd_directory(lobe_path):
	if not os.path.exists(os.path.join(lobe_path, "config", "systemd")):
		os.makedirs(os.path.join(lobe_path, "config", "systemd"))


def setup_main_config(lobe_info, lobe_path):
	# Main config
	lobe_template = lobe.config.env().get_template("systemd/logica-lobe.target")
	lobe_config = lobe_template.render(**lobe_info)
	lobe_config_path = os.path.join(
		lobe_path, "config", "systemd", lobe_info.get("lobe_name") + ".target"
	)

	with open(lobe_config_path, "w") as f:
		f.write(lobe_config)


def setup_workers_config(lobe_info, lobe_path):
	# Worker Group
	lobe_workers_target_template = lobe.config.env().get_template(
		"systemd/logica-lobe-workers.target"
	)
	lobe_default_worker_template = lobe.config.env().get_template(
		"systemd/logica-lobe-logica-default-worker.service"
	)
	lobe_short_worker_template = lobe.config.env().get_template(
		"systemd/logica-lobe-logica-short-worker.service"
	)
	lobe_long_worker_template = lobe.config.env().get_template(
		"systemd/logica-lobe-logica-long-worker.service"
	)
	lobe_schedule_worker_template = lobe.config.env().get_template(
		"systemd/logica-lobe-logica-schedule.service"
	)

	lobe_workers_target_config = lobe_workers_target_template.render(**lobe_info)
	lobe_default_worker_config = lobe_default_worker_template.render(**lobe_info)
	lobe_short_worker_config = lobe_short_worker_template.render(**lobe_info)
	lobe_long_worker_config = lobe_long_worker_template.render(**lobe_info)
	lobe_schedule_worker_config = lobe_schedule_worker_template.render(**lobe_info)

	lobe_workers_target_config_path = os.path.join(
		lobe_path, "config", "systemd", lobe_info.get("lobe_name") + "-workers.target"
	)
	lobe_default_worker_config_path = os.path.join(
		lobe_path,
		"config",
		"systemd",
		lobe_info.get("lobe_name") + "-logica-default-worker@.service",
	)
	lobe_short_worker_config_path = os.path.join(
		lobe_path,
		"config",
		"systemd",
		lobe_info.get("lobe_name") + "-logica-short-worker@.service",
	)
	lobe_long_worker_config_path = os.path.join(
		lobe_path,
		"config",
		"systemd",
		lobe_info.get("lobe_name") + "-logica-long-worker@.service",
	)
	lobe_schedule_worker_config_path = os.path.join(
		lobe_path,
		"config",
		"systemd",
		lobe_info.get("lobe_name") + "-logica-schedule.service",
	)

	with open(lobe_workers_target_config_path, "w") as f:
		f.write(lobe_workers_target_config)

	with open(lobe_default_worker_config_path, "w") as f:
		f.write(lobe_default_worker_config)

	with open(lobe_short_worker_config_path, "w") as f:
		f.write(lobe_short_worker_config)

	with open(lobe_long_worker_config_path, "w") as f:
		f.write(lobe_long_worker_config)

	with open(lobe_schedule_worker_config_path, "w") as f:
		f.write(lobe_schedule_worker_config)


def setup_web_config(lobe_info, lobe_path):
	# Web Group
	lobe_web_target_template = lobe.config.env().get_template(
		"systemd/logica-lobe-web.target"
	)
	lobe_web_service_template = lobe.config.env().get_template(
		"systemd/logica-lobe-logica-web.service"
	)
	lobe_node_socketio_template = lobe.config.env().get_template(
		"systemd/logica-lobe-node-socketio.service"
	)

	lobe_web_target_config = lobe_web_target_template.render(**lobe_info)
	lobe_web_service_config = lobe_web_service_template.render(**lobe_info)
	lobe_node_socketio_config = lobe_node_socketio_template.render(**lobe_info)

	lobe_web_target_config_path = os.path.join(
		lobe_path, "config", "systemd", lobe_info.get("lobe_name") + "-web.target"
	)
	lobe_web_service_config_path = os.path.join(
		lobe_path, "config", "systemd", lobe_info.get("lobe_name") + "-logica-web.service"
	)
	lobe_node_socketio_config_path = os.path.join(
		lobe_path,
		"config",
		"systemd",
		lobe_info.get("lobe_name") + "-node-socketio.service",
	)

	with open(lobe_web_target_config_path, "w") as f:
		f.write(lobe_web_target_config)

	with open(lobe_web_service_config_path, "w") as f:
		f.write(lobe_web_service_config)

	with open(lobe_node_socketio_config_path, "w") as f:
		f.write(lobe_node_socketio_config)


def setup_redis_config(lobe_info, lobe_path):
	# Redis Group
	lobe_redis_target_template = lobe.config.env().get_template(
		"systemd/logica-lobe-redis.target"
	)
	lobe_redis_cache_template = lobe.config.env().get_template(
		"systemd/logica-lobe-redis-cache.service"
	)
	lobe_redis_queue_template = lobe.config.env().get_template(
		"systemd/logica-lobe-redis-queue.service"
	)
	lobe_redis_socketio_template = lobe.config.env().get_template(
		"systemd/logica-lobe-redis-socketio.service"
	)

	lobe_redis_target_config = lobe_redis_target_template.render(**lobe_info)
	lobe_redis_cache_config = lobe_redis_cache_template.render(**lobe_info)
	lobe_redis_queue_config = lobe_redis_queue_template.render(**lobe_info)
	lobe_redis_socketio_config = lobe_redis_socketio_template.render(**lobe_info)

	lobe_redis_target_config_path = os.path.join(
		lobe_path, "config", "systemd", lobe_info.get("lobe_name") + "-redis.target"
	)
	lobe_redis_cache_config_path = os.path.join(
		lobe_path, "config", "systemd", lobe_info.get("lobe_name") + "-redis-cache.service"
	)
	lobe_redis_queue_config_path = os.path.join(
		lobe_path, "config", "systemd", lobe_info.get("lobe_name") + "-redis-queue.service"
	)
	lobe_redis_socketio_config_path = os.path.join(
		lobe_path,
		"config",
		"systemd",
		lobe_info.get("lobe_name") + "-redis-socketio.service",
	)

	with open(lobe_redis_target_config_path, "w") as f:
		f.write(lobe_redis_target_config)

	with open(lobe_redis_cache_config_path, "w") as f:
		f.write(lobe_redis_cache_config)

	with open(lobe_redis_queue_config_path, "w") as f:
		f.write(lobe_redis_queue_config)

	with open(lobe_redis_socketio_config_path, "w") as f:
		f.write(lobe_redis_socketio_config)


def _create_symlinks(lobe_path):
	lobe_dir = os.path.abspath(lobe_path)
	etc_systemd_system = os.path.join("/", "etc", "systemd", "system")
	config_path = os.path.join(lobe_dir, "config", "systemd")
	unit_files = get_unit_files(lobe_dir)
	for unit_file in unit_files:
		filename = "".join(unit_file)
		exec_cmd(
			f'sudo ln -s {config_path}/{filename} {etc_systemd_system}/{"".join(unit_file)}'
		)
	exec_cmd("sudo systemctl daemon-reload")


def _delete_symlinks(lobe_path):
	lobe_dir = os.path.abspath(lobe_path)
	etc_systemd_system = os.path.join("/", "etc", "systemd", "system")
	unit_files = get_unit_files(lobe_dir)
	for unit_file in unit_files:
		exec_cmd(f'sudo rm {etc_systemd_system}/{"".join(unit_file)}')
	exec_cmd("sudo systemctl daemon-reload")


def get_unit_files(lobe_path):
	lobe_name = get_lobe_name(lobe_path)
	unit_files = [
		[lobe_name, ".target"],
		[lobe_name + "-workers", ".target"],
		[lobe_name + "-web", ".target"],
		[lobe_name + "-redis", ".target"],
		[lobe_name + "-logica-default-worker@", ".service"],
		[lobe_name + "-logica-short-worker@", ".service"],
		[lobe_name + "-logica-long-worker@", ".service"],
		[lobe_name + "-logica-schedule", ".service"],
		[lobe_name + "-logica-web", ".service"],
		[lobe_name + "-node-socketio", ".service"],
		[lobe_name + "-redis-cache", ".service"],
		[lobe_name + "-redis-queue", ".service"],
		[lobe_name + "-redis-socketio", ".service"],
	]
	return unit_files
