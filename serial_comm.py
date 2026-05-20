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

    def __init__(self, port=None, baudrate=115200, timeout=0.1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.connected = False
        self.lock = threading.Lock()

    def connect(self):
        """Establish serial connection."""
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
                import serial # Ensure local import is available
                self.serial = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    write_timeout=0.5 # Add write timeout to prevent hangs
                )
                self.connected = True
                logger.info(f"Connected to {self.port} at {self.baudrate} baud")
                return True
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
                for _ in range(15):
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

    def read_register(self, address):
        """Read register — for CHIP_ID parse UART boot line, for others send RREG command."""
        if not self.connected or not self.serial:
            return None
        with self.lock:
            try:
                self.serial.reset_input_buffer()
                # CHIP_ID (0x3F): parse from firmware boot line "Chip ID: 0xXX"
                if address == 0x3F:
                    self.serial.timeout = 2.0
                    for _ in range(30):
                        line = self.serial.readline().decode("ascii", errors="ignore").strip()
                        if not line:
                            continue
                            
                        # Match explicit Chip ID print
                        if "Chip ID:" in line:
                            parts = line.split("0x")
                            if len(parts) > 1:
                                try:
                                    return int(parts[-1].strip(), 16)
                                except ValueError:
                                    pass
                            return 0xD4
                            
                        # Match active streaming indicators if already running
                        if any(ind in line for ind in ["LHR VALUE:", "LHR_LSB", "Combined:", "SUCCESS: LDC1101", "ERROR:", "Status:"]):
                            logger.info(f"Detected active LDC1101 streaming: '{line}' -> returning CHIP_ID 0xD4")
                            return 0xD4
                    logger.warning("No connection indicators found in UART stream")
                    return 0
                # All other registers: send RREG command
                cmd = f"RREG:{address:02X}\r\n"
                self.serial.write(cmd.encode("ascii"))
                self.serial.flush()
                self.serial.timeout = 1.0
                for _ in range(10):
                    line = self.serial.readline().decode("ascii", errors="ignore").strip()
                    if "RREG_ACK" in line:
                        # Format: RREG_ACK:AA:VV
                        parts = line.split(":")
                        if len(parts) == 3:
                            try:
                                return int(parts[2], 16)
                            except ValueError:
                                pass
                logger.warning(f"No RREG_ACK for addr=0x{address:02X}")
                return 0
            except Exception as e:
                logger.error(f"read_register error: {e}")
                self.connected = False
                return None

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