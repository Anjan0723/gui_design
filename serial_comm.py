# ═══════════════════════════════════════════════════════════════
#  SERIAL COMMUNICATION - Serial port handling
# ═══════════════════════════════════════════════════════════════

import logging
import serial.tools.list_ports
import serial


logger = logging.getLogger("LDC1101_Serial")


def get_available_ports():
    """Get list of available COM ports."""
    return [p.device for p in serial.tools.list_ports.comports()]


def get_mock_ports():
    """Get list of mock ports for simulation."""
    return ["COM3 (Mock)", "COM4 (Mock)"]


def refresh_ports(populate_cb, conn_label):
    """
    Refresh available ports and update UI.

    Args:
        populate_cb: Callback to set combobox values
        conn_label: Connection status label widget
    """
    ports = get_available_ports()

    if not ports:
        # Use mock ports when no real ports found
        ports = get_mock_ports()
        populate_cb(ports)
        conn_label.config(text="  NOT CONNECTED  ", bg="#cc0000")
    else:
        populate_cb(ports)
        conn_label.config(text="  CONNECTED  ", bg="#107c10")

    return ports


import threading

class SerialConnection:
    """Handle serial communication with LDC1101."""

    def __init__(self, port=None, baudrate=115200, timeout=1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.connected = False
        self.lock = threading.Lock()

    def connect(self):
        """Establish serial connection.
        
        Opens the port WITHOUT asserting DTR/RTS to avoid resetting the 
        MSP432 board via the XDS110 debugger. Uses two-stage open:
        configure first, then open.
        """
        if self.port is None:
            logger.error("Cannot connect: port is None")
            return False

        # Pre-emptive close to break any existing hangs or locks
        try:
            if self.serial and self.serial.is_open:
                self.serial.close()
        except Exception as e:
            logger.warning(f"Error closing existing serial: {e}")

        with self.lock:
            try:
                import serial as _serial  # Ensure local import is available
                import time
                logger.info(f"Attempting to open {self.port} at {self.baudrate} baud...")
                
                # Two-stage open: configure FIRST, then open.
                # This prevents the default DTR assertion that resets the board.
                ser = _serial.Serial()
                ser.port = self.port
                ser.baudrate = self.baudrate
                ser.timeout = self.timeout
                ser.write_timeout = 2.0
                ser.bytesize = _serial.EIGHTBITS
                ser.parity = _serial.PARITY_NONE
                ser.stopbits = _serial.STOPBITS_ONE
                ser.xonxoff = False
                ser.rtscts = False
                ser.dsrdtr = False
                # Prevent DTR/RTS assertion on open — this is the key fix.
                # Without this, opening the port resets the MSP432 via XDS110.
                ser.dtr = False
                ser.rts = False
                ser.open()
                
                self.serial = ser
                logger.info(f"Port {self.port} opened (DTR/RTS not asserted)")
                
                # Brief stabilization delay
                time.sleep(0.3)
                
                # Drain any buffered flood data (e.g. "ERROR: Oscillation stopped!")
                # so subsequent reads start clean
                drained = 0
                drain_start = time.time()
                while time.time() - drain_start < 1.0:
                    n = self.serial.in_waiting
                    if n > 0:
                        discarded = self.serial.read(n)
                        drained += len(discarded)
                        logger.debug(f"Drained {len(discarded)} bytes of buffered data")
                    else:
                        # Wait a bit to catch any more flood data
                        time.sleep(0.1)
                        if self.serial.in_waiting == 0:
                            break
                
                if drained > 0:
                    logger.info(f"Drained {drained} total bytes of buffered data")
                
                self.serial.reset_input_buffer()
                self.serial.reset_output_buffer()
                self.connected = True
                logger.info(f"Port {self.port} opened successfully, ready for commands")
                return True
            except _serial.SerialException as e:
                logger.error(f"Failed to open {self.port}: {e}")
                self.connected = False
                return False
            except Exception as e:
                logger.error(f"Failed to connect to {self.port}: {e}")
                self.connected = False
                return False

    def disconnect(self):
        """Close serial connection."""
        with self.lock:
            try:
                if self.serial and self.serial.is_open:
                    self.serial.close()
                    logger.info(f"Disconnected from {self.port}")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.connected = False

    def write_register(self, address, value):
        if not self.connected or not self.serial:
            return False
        with self.lock:
            try:
                cmd = f"WREG:{address:02X}:{value:02X}\r\n"
                self.serial.write(cmd.encode("ascii"))
                self.serial.flush()
                self.serial.timeout = 1.5
                for _ in range(50):
                    line = self.serial.readline().decode("ascii", errors="ignore").strip()
                    if "WREG_ACK" in line:
                        logger.info(f"Write ACK: {line}")
                        # Parse readback: WREG_ACK:AA:VV:RB:RR
                        parts = line.split(":")
                        if len(parts) >= 5:
                            try:
                                readback = int(parts[4], 16)
                                if readback == value:
                                    logger.info(f"Readback verified: 0x{readback:02X} ✓")
                                    return True
                                else:
                                    logger.warning(
                                        f"Readback MISMATCH: wrote 0x{value:02X}, "
                                        f"got 0x{readback:02X}"
                                    )
                                    return False   # Write failed silently
                            except ValueError:
                                pass
                        return True
                logger.warning(f"No WREG_ACK for addr=0x{address:02X}")
                return False
            except Exception as e:
                logger.error(f"write_register error: {e}")
                self.connected = False
                return False

    def read_register_fast(self, address, timeout=5.0):
        """
        Read register — handles firmware's continuous UART output.
        Uses aggressive scanning to find RREG_ACK buried in flood.
        """
        if not self.connected or not self.serial:
            return None
        with self.lock:
            try:
                import time

                # Flush stale data first
                self.serial.reset_input_buffer()
                time.sleep(0.02)

                # Send command (twice to ensure it gets through flood)
                cmd = f"RREG:{address:02X}\r\n"
                self.serial.write(cmd.encode("ascii"))
                self.serial.flush()
                logger.debug(f"Sent: {cmd.strip()}")

                # Brief pause then send again in case first got lost
                time.sleep(0.05)
                self.serial.write(cmd.encode("ascii"))
                self.serial.flush()
                logger.debug(f"Sent (retry): {cmd.strip()}")

                # Aggressively scan all available data
                self.serial.timeout = 0.1
                deadline = time.time() + timeout
                buffer = ""
                while time.time() < deadline:
                    try:
                        if self.serial.in_waiting > 0:
                            data = self.serial.read(self.serial.in_waiting)
                            if data:
                                buffer += data.decode("ascii", errors="ignore")
                                while '\n' in buffer:
                                    line, buffer = buffer.split('\n', 1)
                                    line = line.strip()
                                    if not line:
                                        continue
                                    logger.debug(f"RX: {line}")

                                    if "RREG_ACK" in line:
                                        parts = line.split(":")
                                        if len(parts) >= 3:
                                            try:
                                                val = int(parts[2], 16)
                                                logger.info(f"Reg 0x{address:02X} = 0x{val:02X}")
                                                return val
                                            except ValueError:
                                                pass

                                    if "Chip ID:" in line or "chip id" in line.lower():
                                        parts = line.split("0x")
                                        if len(parts) > 1:
                                            try:
                                                val = int(parts[-1].strip()[:2], 16)
                                                logger.info(f"Found CHIP_ID 0x{val:02X}")
                                                return val
                                            except ValueError:
                                                pass
                        else:
                            time.sleep(0.01)
                    except Exception as e:
                        logger.debug(f"Read error: {e}")
                        pass

                logger.warning(f"No RREG_ACK for 0x{address:02X} within {timeout}s")
                return None

            except Exception as e:
                logger.error(f"read_register_fast error: {e}")
                self.connected = False
                return None

    def read_register(self, address):
        """Read register - uses read_register_fast with longer timeout."""
        return self.read_register_fast(address, timeout=5.0)

    def send_csensor(self, pf_value: float):
        """Send Csensor pF value to MCU and wait for ACK."""
        if not self.connected:
            return False
        if self.port and "Mock" in self.port:
            logger.info(f"[Mock] Confirmed Csensor update to {int(pf_value)}pF")
            return True
        if not self.serial:
            return False
        with self.lock:
            try:
                cmd = f"CSENSOR:{int(pf_value)}\r\n"
                self.serial.write(cmd.encode("ascii"))
                self.serial.flush()
                # Wait for ACK line
                self.serial.timeout = 1.0
                for _ in range(10):
                    line = self.serial.readline().decode("ascii", errors="ignore").strip()
                    if "CSENSOR_ACK" in line:
                        logger.info(f"MCU confirmed Csensor: {line}")
                        return True
                logger.warning("No CSENSOR_ACK received from MCU")
                return False
            except Exception as e:
                logger.error(f"send_csensor error: {e}")
                return False

    def read_lhr_data(self):
        """Read LHR_DATA registers 0x38, 0x39, 0x3A via RREG commands."""
        if not self.connected or not self.serial:
            return None
        lsb = self.read_register(0x38)
        mid = self.read_register(0x39)
        msb = self.read_register(0x3A)
        if lsb is None or mid is None or msb is None:
            return None
        return ((msb & 0xFF) << 16) | ((mid & 0xFF) << 8) | (lsb & 0xFF)

    def dump_uart_data(self, timeout=3.0):
        """Dump all raw UART data for debugging - returns all lines received."""
        if not self.connected or not self.serial:
            return []
        lines = []
        with self.lock:
            try:
                old_timeout = self.serial.timeout
                self.serial.timeout = timeout
                logger.info("=== Starting UART dump ===")
                while True:
                    line = self.serial.readline().decode("ascii", errors="ignore").strip()
                    if not line:
                        break
                    logger.info(f"UART: '{line}'")
                    lines.append(line)
                logger.info(f"=== UART dump complete: {len(lines)} lines ===")
                self.serial.timeout = old_timeout
            except Exception as e:
                logger.error(f"UART dump error: {e}")
        return lines

    def peek_buffer(self):
        """Quickly peek at what's in the UART buffer without blocking."""
        if not self.connected or not self.serial:
            return ""
        try:
            data = ""
            self.serial.timeout = 0  # Non-blocking
            while self.serial.in_waiting > 0:
                byte = self.serial.read(1)
                if byte:
                    char = byte.decode("ascii", errors="ignore")
                    data += char
            return data
        except Exception as e:
            logger.error(f"peek_buffer error: {e}")
            return ""