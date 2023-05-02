VERSION = "5.15.1"
PROJECT_NAME = "logica-lobe"
FRAPPE_VERSION = None
current_path = None
updated_path = None
LOG_BUFFER = []


def set_logica_version(lobe_path="."):
	from .utils.app import get_current_logica_version

	global FRAPPE_VERSION
	if not FRAPPE_VERSION:
		FRAPPE_VERSION = get_current_logica_version(lobe_path=lobe_path)
