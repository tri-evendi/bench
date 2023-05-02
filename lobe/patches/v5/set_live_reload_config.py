from lobe.config.common_site_config import update_config


def execute(lobe_path):
	update_config({"live_reload": True}, lobe_path)
