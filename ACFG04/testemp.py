import minimalmodbus
import serial
import serial.tools.list_ports
import time
import logging

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)-15s %(levelname)-8s %(message)s'
    )
    return logging.getLogger('modbus_diagnostic')

def diagnose_modbus_connection(port, slave_id, register_address, register_count):
    logger = setup_logging()
    
    # Test 1: Verify port connection
    logger.info(f"Test 1: Verifying port {port}")
    try:
        ser = serial.Serial(
            port=port,
            baudrate=19200,
            bytesize=8,
            parity=serial.PARITY_NONE,  # Changed from PARITY_EVEN to PARITY_NONE
            stopbits=1,
            timeout=3
        )
        ser.close()
        logger.info("? Serial port can be opened successfully")
    except Exception as e:
        logger.error(f"? Failed to open serial port: {e}")
        return

    # Test 2: Verify Modbus communication
    logger.info("\nTest 2: Testing Modbus communication")
    try:
        instrument = minimalmodbus.Instrument(port, slave_id)
        instrument.serial.baudrate = 19200
        instrument.serial.bytesize = 8
        instrument.serial.parity = serial.PARITY_NONE  # Changed from PARITY_EVEN to PARITY_NONE
        instrument.serial.stopbits = 1
        instrument.serial.timeout = 3
        
        # Enable debug mode to see raw communication
        instrument.debug = True
        
        logger.info(f"Attempting to read {register_count} registers starting from {register_address}")
        try:
            result = instrument.read_registers(register_address, register_count, 3)
            logger.info(f"? Successfully read registers: {result}")
        except Exception as e:
            logger.error(f"? Failed to read registers: {e}")
            
            # Additional diagnostic information
            if "Checksum error" in str(e):
                logger.info("\nChecksum Error Analysis:")
                logger.info("1. Verify the following settings match your device:")
                logger.info("   - Baud rate: 19200")
                logger.info("   - Data bits: 8")
                logger.info("   - Parity: None")  # Updated to reflect new parity setting
                logger.info("   - Stop bits: 1")
                logger.info("2. Check for interference/noise on the RS485 line")
                logger.info("3. Verify the correct slave ID")
                logger.info("4. Check termination resistors")
    
    except Exception as e:
        logger.error(f"? Failed to initialize Modbus instrument: {e}")

def scan_for_devices(port, start_id=1, end_id=247):
    """Scan for active Modbus devices on the bus."""
    logger = setup_logging()
    logger.info(f"Scanning for Modbus devices on {port}...")
    
    found_devices = []
    
    for slave_id in range(start_id, end_id + 1):
        try:
            instrument = minimalmodbus.Instrument(port, slave_id)
            instrument.serial.baudrate = 19200
            instrument.serial.bytesize = 8
            instrument.serial.parity = serial.PARITY_NONE  # Changed from PARITY_EVEN to PARITY_NONE
            instrument.serial.stopbits = 1
            instrument.serial.timeout = 0.3  # Short timeout for scanning
            
            # Try reading a single register
            try:
                instrument.read_register(3960)  # Using your register address
                found_devices.append(slave_id)
                logger.info(f"Found device at ID {slave_id}")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error setting up instrument: {e}")
            break
            
    return found_devices

if __name__ == "__main__":
    logger = setup_logging()
    
    # First scan for available ports
    ports = [p.device for p in serial.tools.list_ports.comports() if "USB" in p.description]
    logger.info(f"Found USB ports: {ports}")
    
    if not ports:
        logger.error("No USB serial ports found!")
        exit(1)
    
    port = ports[0]
    logger.info(f"Using port: {port}")
    
    # Scan for devices
    devices = scan_for_devices(port)
    if devices:
        logger.info(f"Found devices at IDs: {devices}")
        # Test first found device
        diagnose_modbus_connection(port, devices[0], 3960, 2)
    else:
        logger.info("No devices responded to scan")
        # Try with default ID 1
        diagnose_modbus_connection(port, 1, 3960, 2)