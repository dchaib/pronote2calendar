import logging

import pytest
from pydantic import ValidationError

from pronote2calendar.logging_manager import setup_logging
from pronote2calendar.settings import Settings


@pytest.fixture
def logging_state(monkeypatch):
    root = logging.getLogger()
    app = logging.getLogger("pronote2calendar")
    handlers, root_level, app_level = root.handlers[:], root.level, app.level
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    yield
    for handler in root.handlers[:]:
        if handler not in handlers:
            root.removeHandler(handler)
            handler.close()
    root.handlers[:] = handlers
    root.setLevel(root_level)
    app.setLevel(app_level)


@pytest.mark.usefixtures("logging_state")
@pytest.mark.parametrize(
    "environment,configured,expected",
    [
        (None, "INFO", logging.INFO),
        (None, "DEBUG", logging.DEBUG),
        ("ERROR", "DEBUG", logging.ERROR),
    ],
)
def test_level_precedence(monkeypatch, environment, configured, expected):
    if environment is not None:
        monkeypatch.setenv("LOG_LEVEL", environment)
    setup_logging(configured)
    assert (
        logging.getLogger("pronote2calendar.pronote_client").getEffectiveLevel()
        == expected
    )
    assert logging.getLogger("urllib3").getEffectiveLevel() == logging.WARNING


@pytest.mark.usefixtures("logging_state")
def test_reconfiguration_keeps_dependencies_quiet(capsys):
    setup_logging("DEBUG")
    setup_logging("INFO")
    logging.getLogger("pronote2calendar").debug("hidden diagnostic")
    logging.getLogger("pronote2calendar").info("visible summary")
    logging.getLogger("urllib3").debug("network diagnostic")
    logging.getLogger("urllib3").warning("network warning")
    output = capsys.readouterr().out
    assert "hidden diagnostic" not in output
    assert output.count("visible summary") == 1
    assert "network diagnostic" not in output
    assert output.count("network warning") == 1


@pytest.mark.usefixtures("logging_state")
def test_invalid_environment_and_error_fallback(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBIG")
    with pytest.raises(ValueError, match="Invalid log level"):
        setup_logging()
    setup_logging("ERROR", use_environment=False)
    assert logging.getLogger("pronote2calendar").getEffectiveLevel() == logging.ERROR


def test_invalid_yaml_level(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text(
        "google_calendar:\n  calendar_id: test@example.com\nlog_level: DEBIG\n"
    )
    with pytest.raises(ValidationError):
        Settings()
