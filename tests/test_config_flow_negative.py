from unittest.mock import patch

from homeassistant import config_entries

from custom_components.escpos_printer.const import CONF_PRINTER_NAME, CONF_TIMEOUT, DOMAIN


async def test_config_flow_cannot_connect(hass):  # type: ignore[no-untyped-def]
    with (
        patch(
            "custom_components.escpos_printer.config_flow.get_cups_printers",
            return_value=["TestPrinter"],
        ),
        patch(
            "custom_components.escpos_printer.config_flow.is_cups_printer_available",
            return_value=False,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        # Submit CUPS server step (default localhost), then pick a printer
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        assert result["type"] == "form"
        assert result["step_id"] == "printer"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PRINTER_NAME: "TestPrinter", CONF_TIMEOUT: 1.0}
        )
    assert result["type"] == "form"
    assert result["errors"].get("base") == "cannot_connect"


async def test_config_flow_cups_unavailable(hass):  # type: ignore[no-untyped-def]
    """A connection-level CUPS failure surfaces as cups_unavailable."""
    from custom_components.escpos_printer.printer import CupsError

    with patch(
        "custom_components.escpos_printer.config_flow.async_check_cups",
        side_effect=CupsError("connect", "connection refused"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"].get("base") == "cups_unavailable"


async def test_config_flow_pyipp_missing(hass):  # type: ignore[no-untyped-def]
    """A missing pyipp library surfaces as its own error key."""
    from custom_components.escpos_printer.printer import CupsError

    with patch(
        "custom_components.escpos_printer.config_flow.async_check_cups",
        side_effect=CupsError("pyipp_missing", "No module named 'pyipp'"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["errors"].get("base") == "cups_pyipp_missing"
