from dataclasses import dataclass


@dataclass
class DeyeConfig:
    base_url: str
    app_id: str
    app_secret: str
    email: str
    password: str
    sync_stations_on_poll: bool = False

    def __str__(self):
        return (
            f"DeyeConfig(base_url='{self.base_url}', app_id='{self.app_id}', "
            f"app_secret='***', email='{self.email}', password='***', "
            f"sync_stations_on_poll={self.sync_stations_on_poll})"
        )
