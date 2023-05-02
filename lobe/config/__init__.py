"""Module for setting up system and respective lobe configurations"""


def env():
	from jinja2 import Environment, PackageLoader

	return Environment(loader=PackageLoader("lobe.config"))
