"""Tests for shared/utils/registration.py."""
import os
import logging
from unittest.mock import patch, MagicMock

from shared.utils.registration import load_and_register_modules


class TestLoadAndRegisterModules:
    def test_loads_python_files(self, tmp_path):
        # Create a test module
        module_file = tmp_path / "test_module.py"
        module_file.write_text("def register(app):\n    pass\n")

        calls = []

        def register(app):
            calls.append(app)

        mock_module = MagicMock()
        mock_module.register = register

        with patch("shared.utils.registration.import_module", return_value=mock_module):
            load_and_register_modules(str(tmp_path), "test_package", "register", "arg1")

            assert calls == ["arg1"]

    def test_skips_init_file(self, tmp_path):
        init_file = tmp_path / "__init__.py"
        init_file.write_text("")
        module_file = tmp_path / "test_module.py"
        module_file.write_text("def register(app):\n    pass\n")

        calls = []

        def register(app):
            calls.append(app)

        mock_module = MagicMock()
        mock_module.register = register

        with patch("shared.utils.registration.import_module", return_value=mock_module):
            load_and_register_modules(str(tmp_path), "test_package", "register")

            # Should only import test_module, not __init__
            assert calls == []

    def test_skips_non_python_files(self, tmp_path):
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("not python")
        module_file = tmp_path / "test_module.py"
        module_file.write_text("def register(app):\n    pass\n")

        calls = []

        def register(app):
            calls.append(app)

        mock_module = MagicMock()
        mock_module.register = register

        with patch("shared.utils.registration.import_module", return_value=mock_module):
            load_and_register_modules(str(tmp_path), "test_package", "register")

            assert calls == []

    def test_warns_when_register_method_missing(self, tmp_path):
        module_file = tmp_path / "test_module.py"
        module_file.write_text("def some_other_func():\n    pass\n")

        mock_module = MagicMock()
        del mock_module.register

        with patch("shared.utils.registration.import_module", return_value=mock_module):
            with patch("shared.utils.registration.logger") as mock_logger:
                load_and_register_modules(str(tmp_path), "test_package", "register")
                mock_logger.warning.assert_called_once()

    def test_continues_on_exception(self, tmp_path):
        module_file = tmp_path / "test_module.py"
        module_file.write_text("def register(app):\n    pass\n")

        with patch("shared.utils.registration.import_module", side_effect=Exception("Import error")):
            with patch("shared.utils.registration.logger") as mock_logger:
                load_and_register_modules(str(tmp_path), "test_package", "register")
                mock_logger.error.assert_called_once()

    def test_passes_kwargs(self, tmp_path):
        module_file = tmp_path / "test_module.py"
        module_file.write_text("def register(app, config=None):\n    pass\n")

        calls = []

        def register(app, config=None):
            calls.append((app, config))

        mock_module = MagicMock()
        mock_module.register = register

        with patch("shared.utils.registration.import_module", return_value=mock_module):
            load_and_register_modules(
                str(tmp_path), "test_package", "register",
                "arg1", config="my_config"
            )

            assert calls == [("arg1", "my_config")]

    def test_filters_kwargs_by_signature(self, tmp_path):
        module_file = tmp_path / "test_module.py"
        module_file.write_text("def register(app):\n    pass\n")

        calls = []

        def register(app):
            calls.append(app)

        mock_module = MagicMock()
        mock_module.register = register

        with patch("shared.utils.registration.import_module", return_value=mock_module):
            load_and_register_modules(
                str(tmp_path), "test_package", "register",
                "arg1", config="my_config", extra="ignored"
            )

            # config and extra should be filtered out since register only accepts app
            assert calls == ["arg1"]
