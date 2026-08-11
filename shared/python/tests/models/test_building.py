"""Tests for shared/models/building.py."""
from shared.models.building import Building


class TestBuildingFields:
    def test_has_name_field(self):
        assert "name" in Building.model_fields

    def test_has_color_field(self):
        assert "color" in Building.model_fields

    def test_has_enabled_field(self):
        assert "enabled" in Building.model_fields

    def test_has_station_field(self):
        assert "station" in Building.model_fields

    def test_station_defaults_none(self):
        assert Building.model_fields["station"].default is None

    def test_has_report_users_field(self):
        assert "report_users" in Building.model_fields

    def test_report_users_defaults_empty_list(self):
        assert Building.model_fields["report_users"].default == []

    def test_has_order_field(self):
        assert "order" in Building.model_fields

    def test_order_defaults_1(self):
        assert Building.model_fields["order"].default == 1

    def test_settings_name(self):
        assert Building.Settings.name == "buildings"


class TestBuildingToDict:
    def test_to_dict_with_no_station(self):
        from shared.models.localizable_value import LocalizableValue
        building = Building(
            name=LocalizableValue.model_validate({"en": "Test Building"}),
            color="#ff0000",
            enabled=True,
            order=1,
        )
        d = building.to_dict()
        assert d["name"].root == {"en": "Test Building"}
        assert d["color"] == "#ff0000"
        assert d["station_id"] is None
        assert d["report_user_ids"] == []
        assert d["order"] == 1
