# ESC/POS Printer Integration Examples

Example scripts demonstrating how to use the ESC/POS Thermal Printer integration with Home Assistant.

## Available Examples

### 1. Test Printer Scripts (`test_printer_script.yaml`)

Comprehensive test scripts for verifying printer functionality:
- **test_escpos_printer** - Full feature test (text, alignment, formatting, QR, barcode, image)
- **test_escpos_quick** - Quick text print test
- **test_escpos_qr** - QR code test
- **test_escpos_barcode** - Barcode test
- **test_escpos_image** - Image print test
- **test_escpos_beep** - Buzzer test
- **test_escpos_receipt_demo** - Sample receipt-style printout

### 2. Mealie Shopping List Printer (`mealie_shopping_list_printer.yaml`)

Print your Mealie shopping list to a receipt printer with AI-powered categorization.

**Features:**
- Fetches shopping list from Mealie via the Home Assistant Mealie integration
- Sends items to OpenAI for smart categorization by grocery store section
- Prints a nicely formatted receipt with checkboxes for each item

**Prerequisites:**
1. [Mealie integration](https://github.com/mealie-recipes/mealie) installed via HACS
2. [OpenAI Conversation integration](https://www.home-assistant.io/integrations/openai_conversation/) configured
3. This ESC/POS Thermal Printer integration installed and configured

**Available Scripts:**
- **print_mealie_shopping_list** - Uses OpenAI Conversation integration
- **print_mealie_shopping_list_rest** - Uses direct OpenAI REST API

## Installation

1. Copy the desired `.yaml` file to your Home Assistant config directory
2. Include it in your `configuration.yaml`:

```yaml
script: !include examples/mealie_shopping_list_printer.yaml
```

Or merge with existing scripts:

```yaml
script: !include_dir_merge_named scripts/
```

3. Restart Home Assistant
4. Update entity IDs in the scripts to match your setup

## Usage

Call scripts from:
- Developer Tools > Services
- Dashboard buttons
- Automations
- Voice assistants (Google Home, Alexa via HA)

Example automation trigger:

```yaml
automation:
  - alias: "Print shopping list when leaving home"
    trigger:
      - platform: zone
        entity_id: person.you
        zone: zone.home
        event: leave
    action:
      - service: script.print_mealie_shopping_list
```

## Sample Output

```
      SHOPPING LIST
   January 15, 2025 at 3:30 PM
          12 items
================================

PRODUCE
--------------------------------
[ ] Apples
[ ] Bananas
[ ] Spinach
[ ] Carrots

DAIRY & EGGS
--------------------------------
[ ] Milk
[ ] Eggs
[ ] Butter

MEAT & SEAFOOD
--------------------------------
[ ] Chicken breast
[ ] Ground beef

BAKERY
--------------------------------
[ ] Bread
[ ] Bagels

PANTRY & CANNED GOODS
--------------------------------
[ ] Pasta

================================
     Happy Shopping!
================================
```
