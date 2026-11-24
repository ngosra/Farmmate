from django.conf import settings


class SatelliteError(Exception):
    pass


class SatelliteProvider:
    """Provider boundary. FarmMate stores satellite rows only when a provider returns them."""

    code = "none"

    @property
    def reason(self) -> str:
        configured = (settings.SATELLITE_PROVIDER or "none").strip() or "none"
        if configured in {"", "none"}:
            return (
                "No satellite provider is configured. Set SATELLITE_PROVIDER and its credentials. "
                "FarmMate does not invent observations."
            )
        return (
            f"Satellite provider '{configured}' is not available. "
            "FarmMate does not invent observations."
        )

    def configured(self) -> bool:
        return False

    def fetch(self, field):
        raise SatelliteError(self.reason)


def get_provider() -> SatelliteProvider:
    return SatelliteProvider()
