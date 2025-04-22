"""Uiot Config api."""


class UIOTConfig:
    """UIOT Config."""

    app_key: str = ""
    app_secret: str = ""
    access_token: str = ""
    request_url: str = ""
    third_sn: str = ""
    third_name: str = ""

    host_sn: str = ""

    def __init__(
        self,
        url: str,
        access_token: str,
        app_key: str,
        app_secret: str,
        third_name: str,
        third_sn: str,
        host_sn: str,
    ) -> None:
        """UIOT Config ini."""
        self.request_url = url
        self.access_token = access_token
        self.app_key = app_key
        self.app_secret = app_secret
        self.third_name = third_name
        self.third_sn = third_sn
        self.host_sn = host_sn
