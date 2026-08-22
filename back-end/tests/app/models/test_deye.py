"""Tests for app/models/deye.py."""
from app.models.deye import DeyeConnectionStatus, DeyeStation, DeyeStationList, DeyeStationData


class TestDeyeConnectionStatus:
    def test_normal_value(self):
        assert DeyeConnectionStatus.NORMAL.value == "NORMAL"

    def test_no_device_value(self):
        assert DeyeConnectionStatus.NO_DEVICE.value == "NO_DEVICE"

    def test_all_offline_value(self):
        assert DeyeConnectionStatus.ALL_OFFLINE.value == "ALL_OFFLINE"

    def test_partial_offline_value(self):
        assert DeyeConnectionStatus.PARTIAL_OFFLINE.value == "PARTIAL_OFFLINE"

    def test_is_str_enum(self):
        assert isinstance(DeyeConnectionStatus.NORMAL, str)


class TestDeyeStation:
    def test_minimal_station(self):
        station = DeyeStation(id=1, name="Test Station")
        assert station.id == 1
        assert station.name == "Test Station"
        assert station.owner_name is None
        assert station.battery_soc is None
        assert station.connection_status is None

    def test_full_station(self):
        station = DeyeStation(
            id=1,
            name="Test Station",
            ownerName="Owner",
            batterySOC=85.5,
            connectionStatus="NORMAL",
            contactPhone="+1234567890",
            createdDate=1234567890.0,
            generationPower=5000.0,
            gridInterconnectionType="Type A",
            installedCapacity=10000.0,
            lastUpdateTime=1234567890.0,
            locationAddress="123 Main St",
            locationLat=40.7128,
            locationLng=-74.0060,
            regionNationId=1,
            regionTimezone="UTC",
            startOperatingTime=1234567890.0,
        )
        assert station.owner_name == "Owner"
        assert station.battery_soc == 85.5
        assert station.connection_status == DeyeConnectionStatus.NORMAL
        assert station.contact_phone == "+1234567890"
        assert station.generation_power == 5000.0
        assert station.installed_capacity == 10000.0
        assert station.location_lat == 40.7128
        assert station.location_lng == -74.0060

    def test_extra_fields_ignored(self):
        station = DeyeStation(id=1, name="Test", extra_field="ignored")
        assert station.id == 1
        assert station.name == "Test"

    def test_populate_by_name(self):
        station = DeyeStation(id=1, name="Test", battery_soc=50.0)
        assert station.battery_soc == 50.0


class TestDeyeStationList:
    def test_minimal_list(self):
        lst = DeyeStationList(
            code="0",
            msg="success",
            requestId="req-123",
            success=True,
            total=0,
        )
        assert lst.code == "0"
        assert lst.msg == "success"
        assert lst.request_id == "req-123"
        assert lst.success is True
        assert lst.total == 0
        assert lst.station_list == []

    def test_with_stations(self):
        station = DeyeStation(id=1, name="Test")
        lst = DeyeStationList(
            code="0",
            msg="success",
            requestId="req-123",
            success=True,
            total=1,
            stationList=[station],
        )
        assert len(lst.station_list) == 1
        assert lst.station_list[0].name == "Test"


class TestDeyeStationData:
    def test_minimal_data(self):
        data = DeyeStationData(
            code="0",
            msg="success",
            requestId="req-123",
            success=True,
            lastUpdateTime=1234567890.0,
        )
        assert data.code == "0"
        assert data.msg == "success"
        assert data.request_id == "req-123"
        assert data.success is True
        assert data.last_update_time == 1234567890.0

    def test_full_data(self):
        data = DeyeStationData(
            batteryPower=100.0,
            batterySOC=85.0,
            chargePower=500.0,
            code="0",
            consumptionPower=2000.0,
            dischargePower=1500.0,
            generationPower=3000.0,
            gridPower=500.0,
            irradiateIntensity=800.0,
            lastUpdateTime=1234567890.0,
            msg="success",
            purchasePower=1000.0,
            requestId="req-123",
            success=True,
            wirePower=2500.0,
        )
        assert data.battery_power == 100.0
        assert data.battery_soc == 85.0
        assert data.charge_power == 500.0
        assert data.consumption_power == 2000.0
        assert data.discharge_power == 1500.0
        assert data.generation_power == 3000.0
        assert data.grid_power == 500.0
        assert data.irradiate_intensity == 800.0
        assert data.purchase_power == 1000.0
        assert data.wire_power == 2500.0

    def test_extra_fields_ignored(self):
        data = DeyeStationData(
            code="0",
            msg="success",
            requestId="req-123",
            success=True,
            lastUpdateTime=1234567890.0,
            extra_field="ignored",
        )
        assert data.code == "0"
