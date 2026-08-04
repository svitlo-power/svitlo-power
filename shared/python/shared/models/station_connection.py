from beanie import Document
from pydantic import Field


class StationConnection(Document):
    name: str = Field(max_length=128)
    base_url: str = Field(max_length=256)
    app_id: str = Field(max_length=128)
    # app_secret and password are stored encrypted with the application SECRET_KEY
    app_secret: str
    email: str = Field(max_length=256)
    password: str
    sync_stations_on_poll: bool = False

    class Settings:
        name = "station_connections"

    def __str__(self):
        return (
            f"StationConnection(id={self.id}, name='{self.name}', base_url='{self.base_url}', "
            f"app_id='{self.app_id}', app_secret='***', email='{self.email}', password='***', "
            f"sync_stations_on_poll={self.sync_stations_on_poll})"
        )
