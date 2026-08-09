# ESC/POS Output Parsing & Validation Toolkit

Transport-independent building blocks for validating the ESC/POS byte stream
the integration generates.

> **History:** This directory used to contain a full integration-test framework
> built around a direct-TCP ESC/POS printer emulator (a virtual printer
> listening on port 9100, connection/resilience error simulation, and a Home
> Assistant socket harness). The integration now submits jobs to **CUPS over
> IPP**, so that socket-transport machinery no longer exercised the real
> submission path and was removed. Only the reusable, transport-independent
> pieces are kept here.

## What's here

```
integration_tests/
├── emulator/
│   ├── command_parser.py    # Parses an ESC/POS byte stream into commands
│   └── printer_state.py     # Command / PrintJob / PrinterState models
└── fixtures/
    ├── mock_data_generator.py  # Generates ESC/POS test content
    └── verification_utils.py   # Asserts on parsed commands / print jobs
```

- **`EscposCommandParser`** turns raw ESC/POS bytes (text, alignment, cut, feed,
  barcode, image, QR, codepage, etc.) into structured command dicts.
- **`PrinterState`** consumes parsed `Command` objects and tracks a command log
  and print history (`PrintJob`s) for assertions.
- **`VerificationUtilities`** provides helpers such as `verify_printer_received`,
  `verify_print_content`, and `verify_command_sequence`.
- **`MockDataGenerator`** produces realistic text, QR, barcode, and image test
  inputs.

## Intended use

These modules have no network or Home Assistant dependencies. They are meant as
a starting point for a future CUPS/IPP-based test suite: capture the ESC/POS
bytes the integration buffers (the `Dummy` printer output submitted to CUPS),
feed them through `EscposCommandParser` into a `PrinterState`, and assert on the
result with `VerificationUtilities`.

Example:

```python
from tests.integration_tests import (
    Command, EscposCommandParser, PrinterState, VerificationUtilities,
)
from datetime import datetime

parser = EscposCommandParser()
state = PrinterState()

# `data` is the ESC/POS byte stream produced by the integration.
command = parser.parse_command(data)
while command:
    await state.update_state(Command(
        timestamp=datetime.now(),
        command_type=command["type"],
        raw_data=command["raw_data"],
        parameters=command["parameters"],
    ))
    command = parser.parse_command(b"")

log = await state.get_command_log()
assert VerificationUtilities.verify_printer_received("text", [], log)
```
