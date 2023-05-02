# imports - third party imports
import click

# imports - module imports
from lobe.utils.cli import (
	MultiCommandGroup,
	print_lobe_version,
	use_experimental_feature,
	setup_verbosity,
)


@click.group(cls=MultiCommandGroup)
@click.option(
	"--version",
	is_flag=True,
	is_eager=True,
	callback=print_lobe_version,
	expose_value=False,
)
@click.option(
	"--use-feature",
	is_eager=True,
	callback=use_experimental_feature,
	expose_value=False,
)
@click.option(
	"-v",
	"--verbose",
	is_flag=True,
	callback=setup_verbosity,
	expose_value=False,
)
def lobe_command(lobe_path="."):
	import lobe

	lobe.set_logica_version(lobe_path=lobe_path)


from lobe.commands.make import (
	drop,
	exclude_app_for_update,
	get_app,
	include_app_for_update,
	init,
	new_app,
	pip,
	remove_app,
)

lobe_command.add_command(init)
lobe_command.add_command(drop)
lobe_command.add_command(get_app)
lobe_command.add_command(new_app)
lobe_command.add_command(remove_app)
lobe_command.add_command(exclude_app_for_update)
lobe_command.add_command(include_app_for_update)
lobe_command.add_command(pip)


from lobe.commands.update import (
	retry_upgrade,
	switch_to_branch,
	switch_to_develop,
	update,
)

lobe_command.add_command(update)
lobe_command.add_command(retry_upgrade)
lobe_command.add_command(switch_to_branch)
lobe_command.add_command(switch_to_develop)


from lobe.commands.utils import (
	backup_all_sites,
	lobe_src,
	disable_production,
	download_translations,
	find_lobees,
	migrate_env,
	renew_lets_encrypt,
	restart,
	set_mariadb_host,
	set_nginx_port,
	set_redis_cache_host,
	set_redis_queue_host,
	set_redis_socketio_host,
	set_ssl_certificate,
	set_ssl_certificate_key,
	set_url_root,
	start,
)

lobe_command.add_command(start)
lobe_command.add_command(restart)
lobe_command.add_command(set_nginx_port)
lobe_command.add_command(set_ssl_certificate)
lobe_command.add_command(set_ssl_certificate_key)
lobe_command.add_command(set_url_root)
lobe_command.add_command(set_mariadb_host)
lobe_command.add_command(set_redis_cache_host)
lobe_command.add_command(set_redis_queue_host)
lobe_command.add_command(set_redis_socketio_host)
lobe_command.add_command(download_translations)
lobe_command.add_command(backup_all_sites)
lobe_command.add_command(renew_lets_encrypt)
lobe_command.add_command(disable_production)
lobe_command.add_command(lobe_src)
lobe_command.add_command(find_lobees)
lobe_command.add_command(migrate_env)

from lobe.commands.setup import setup

lobe_command.add_command(setup)


from lobe.commands.config import config

lobe_command.add_command(config)

from lobe.commands.git import remote_reset_url, remote_set_url, remote_urls

lobe_command.add_command(remote_set_url)
lobe_command.add_command(remote_reset_url)
lobe_command.add_command(remote_urls)

from lobe.commands.install import install

lobe_command.add_command(install)
