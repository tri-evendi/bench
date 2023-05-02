# imports - standard imports
import os

# imports - third party imports
import click

# imports - module imports
import lobe
from lobe.app import use_rq
from lobe.utils import which
from lobe.lobe import Lobe


def setup_procfile(lobe_path, yes=False, skip_redis=False):
	config = Lobe(lobe_path).conf
	procfile_path = os.path.join(lobe_path, "Procfile")
	if not yes and os.path.exists(procfile_path):
		click.confirm(
			"A Procfile already exists and this will overwrite it. Do you want to continue?",
			abort=True,
		)

	procfile = (
		lobe.config.env()
		.get_template("Procfile")
		.render(
			node=which("node") or which("nodejs"),
			use_rq=use_rq(lobe_path),
			webserver_port=config.get("webserver_port"),
			CI=os.environ.get("CI"),
			skip_redis=skip_redis,
			workers=config.get("workers", {}),
		)
	)

	with open(procfile_path, "w") as f:
		f.write(procfile)
