# Troubleshooting

Solutions for common issues with the ESC/POS Thermal Printer integration.

## Table of Contents

- [Connection Issues](#connection-issues)
- [Print Quality Problems](#print-quality-problems)
- [Service Errors](#service-errors)
- [Image Issues](#image-issues)
- [Paper and Cutting](#paper-and-cutting)
- [Multiple Printers](#multiple-printers)
- [Debug Logging](#debug-logging)
- [Printer-Specific Issues](#printer-specific-issues)

---

## Connection Issues

### "Cannot connect to printer"

**Check network connectivity:**

```bash
# From the Home Assistant host or container
ping <PRINTER_IP>

# Test the printer port
telnet <PRINTER_IP> 9100
```

If telnet connects and shows a blank screen, the printer is reachable. Press
Ctrl+] then type `quit` to exit.

**Common causes:**

1. **Wrong IP address** - Print a network status page from your printer to
verify the IP
2. **Printer is off or sleeping** - Some printers enter sleep mode; try printing
a test page from the printer itself
3. **Firewall blocking port 9100** - Check firewall rules on your network
4. **Printer on different subnet** - Make sure Home Assistant can reach the
printer's network

**Solutions:**

- Increase the timeout value in integration options (try 8-10 seconds)
- Assign a static IP to your printer to prevent IP changes
- Check that port 9100 is not blocked by your router or firewall

### Connection works sometimes, fails other times

**Possible causes:**

- DHCP lease expiring and printer getting a new IP
- Printer entering sleep mode
- Network congestion or instability

**Solutions:**

- Assign a static IP address to the printer
- Disable sleep mode on the printer if possible
- Enable the "Keep Alive" option (experimental)
- Use the Status Interval option to detect when the printer goes offline

### "Connection refused"

The printer is reachable but rejecting connections.

**Check:**

- Another application might be using the printer
- The printer might have a connection limit
- The printer might be in an error state (paper out, cover open)

Try power cycling the printer.

---

## Print Quality Problems

### Garbled or wrong characters

The codepage setting doesn't match your printer.

**Solutions:**

1. Try a different codepage in the integration options
2. Use the `print_text_utf8` service for text with special characters
3. Check your printer's documentation for supported codepages

**Common codepage choices:**

- CP437 - US English, good for basic ASCII
- CP850 - Western European languages
- CP1252 - Windows Western European

### Special characters not printing

Your text contains characters not supported by the printer's codepage.

**Solution:** Use `escpos_printer.print_text_utf8` instead of `print_text`. This
service automatically converts unsupported characters to their closest equivalents.

Characters like curly quotes, em-dashes, and accented letters will be converted:

- "smart quotes" become "straight quotes"
- em-dash becomes --
- accented letters are simplified when necessary

### Text is cut off or wrapping incorrectly

The line width setting doesn't match your printer.

**Solutions:**

1. Check your printer's documentation for characters per line
2. Adjust the Line Width setting in integration options
3. Common values: 32 (58mm paper), 42-48 (80mm paper)

### Print is too light or too dark

This is a hardware setting on the printer, not something the integration controls.

**Solutions:**

- Check your printer's settings menu for print density
- Some printers have DIP switches for density
- Thermal paper quality affects print darkness

---

## Service Errors

### "Service not found"

The integration isn't loaded properly.

**Solutions:**

1. Restart Home Assistant
2. Check **Settings** > **Devices & services** to verify the integration is loaded
3. Check the Home Assistant logs for errors during startup

### "No valid ESC/POS printer targets found"

You're using device targeting but no valid printer was found.

**Possible causes:**

- The device ID is incorrect
- The printer's config entry isn't loaded
- The entity/area doesn't belong to an ESC/POS printer

**Solutions:**

1. Verify the device ID in **Settings** > **Devices & services** > click your printer
2. Try omitting the `target` parameter to broadcast to all printers
3. Check that the printer is properly configured and online

### "Printer configuration not found"

The printer was removed or the integration was reloaded.

**Solutions:**

1. Restart Home Assistant
2. Remove and re-add the integration

### Timeout errors during printing

The printer is taking too long to respond.

**Solutions:**

1. Increase the timeout value in integration options
2. Check network connectivity
3. Reduce image size or complexity
4. The printer might be processing a large print job

---

## Image Issues

### "Image too large"

The image exceeds the maximum allowed size.

**Solutions:**

1. Resize the image to under 512 pixels wide
2. Use an image editor to reduce file size
3. Images are automatically resized, but very large files may be rejected

### Image doesn't print

**Common causes:**

- Unsupported image format
- Image URL not accessible from Home Assistant
- Local path doesn't exist

**Solutions:**

1. Use PNG or JPEG format
2. For URLs, verify the URL is accessible from the HA host
3. For local files, use absolute paths starting with `/config/`
4. Check that the file exists: **Developer Tools** > **Terminal** (if available)

### Image quality is poor

Thermal printers have limited resolution and only print in black and white.

**Tips:**

- Use simple graphics with high contrast
- Black and white images work better than grayscale
- Line art prints better than photos
- Keep images small - 200-300 pixels wide is often enough

### Image prints as solid black

The image is too dark or has no transparency handling.

**Solutions:**

- Use images with white backgrounds instead of transparent
- Increase contrast in the image
- Convert to 1-bit black and white before printing

---

## Paper and Cutting

### Paper doesn't cut

**Possible causes:**

- Printer doesn't have an auto-cutter
- Cutter is disabled in printer settings
- Paper type doesn't work with cutter

**Solutions:**

1. Verify your printer has a cutter (not all do)
2. Try `partial` cut instead of `full`
3. Check printer documentation for cutter settings

### Partial cut leaves too much paper attached

This is normal behavior for partial cut. If you need a cleaner cut, use
`full` cut mode.

### Paper jams during cutting

**Solutions:**

- Make sure you're using the correct paper width
- Check for paper debris in the cutter mechanism
- Some cheap paper doesn't cut well

---

## Multiple Printers

### Services go to wrong printer

When you have multiple printers, always use the `target` parameter to specify
which one.

**Example:**

```yaml
service: escpos_printer.print_text
target:
  device_id: correct_printer_id
data:
  text: "Hello"
```

### Broadcast not reaching all printers

Verify all printers are:

1. Properly configured in the integration
2. Online and reachable
3. Not in an error state

Check the binary sensor for each printer to see their status.

### Can't find device ID

1. Go to **Settings** > **Devices & services**
2. Click on "ESC/POS Thermal Printer"
3. Click on the printer
4. The device ID is in your browser's URL bar

---

## Debug Logging

Enable debug logging to get detailed information about what's happening.

### Enable Debug Logs

Add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.escpos_printer: debug
    escpos: debug
```

Restart Home Assistant to apply.

### View Logs

Go to **Settings** > **System** > **Logs**

Or use the command line:

```bash
# For Home Assistant OS
ha core logs | grep escpos

# For Docker
docker logs homeassistant 2>&1 | grep escpos
```

### What to look for

- Connection errors show network issues
- "Service call" messages show what's being sent to the printer
- "Transcoded text" messages show UTF-8 conversion details
- Exception tracebacks show the exact error

---

## Printer-Specific Issues

### Epson TM Series

**ESC/POS mode:** Make sure the printer is in ESC/POS mode, not Epson
proprietary mode. Check DIP switch settings.

**Network config:** Print a network status page by holding the feed button
during power-on.

### Star Micronics

**Emulation mode:** Verify the printer is set to ESC/POS emulation, not Star
native mode.

**Interface settings:** Check the printer's web interface (if available) for
network settings.

### Generic/Unbranded Printers

**Start simple:** Use the "Auto-detect" profile and basic print_text calls first.

**Codepage:** Try CP437 first, then CP850 if you need European characters.

**Features:** Some cheap printers don't support all ESC/POS commands. If a
feature doesn't work (like QR codes), the printer may not support it.

---

## Getting More Help

If you've tried these solutions and still have issues:

1. **Enable debug logging** and capture relevant log entries
2. **Check existing issues** on [GitHub Issues](https://github.com/cognitivegears/ha-escpos-thermal-printer/issues)
3. **Create a new issue** with:
   - Your printer model
   - Home Assistant version
   - Integration version
   - Debug log output
   - Steps to reproduce the problem
