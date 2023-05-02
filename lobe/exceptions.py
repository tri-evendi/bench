class InvalidBranchException(Exception):
	pass


class InvalidRemoteException(Exception):
	pass


class PatchError(Exception):
	pass


class CommandFailedError(Exception):
	pass


class LobeNotFoundError(Exception):
	pass


class ValidationError(Exception):
	pass


class AppNotInstalledError(ValidationError):
	pass


class CannotUpdateReleaseLobe(ValidationError):
	pass


class FeatureDoesNotExistError(CommandFailedError):
	pass


class NotInLobeDirectoryError(Exception):
	pass


class VersionNotFound(Exception):
	pass
