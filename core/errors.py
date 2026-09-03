class NORYXError(Exception):
    """Base exception for controlled NORYX7 runtime failures."""


class ContractViolation(NORYXError):
    pass


class PolicyDenied(NORYXError):
    pass


class RouteError(NORYXError):
    pass


class VerificationFailure(NORYXError):
    pass
