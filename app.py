import os
import json
import logging
import threading
import time
import miniupnpc
import socket
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename

# Configure logging
LOG_DIR = os.environ.get('LOG_DIR', './logs')
PORTS_FILE = os.environ.get('PORTS_FILE', './ports_data/ports.json')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'upnp-manager.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__) 
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

PORT = int(os.environ.get('PORT', 5000))

# Global variables for monitoring
upnp_monitor_thread = None
last_upnp_check = None
upnp_available = False
port_restoration_enabled = True

def ensure_directories_exist():
    """Ensure required directories exist"""
    try:
        os.makedirs(os.path.dirname(PORTS_FILE), exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)
        if not os.path.exists(PORTS_FILE):
            with open(PORTS_FILE, 'w') as f:
                json.dump([], f)
        logger.info("Directory structure initialized")
    except Exception as e:
        logger.error(f"Failed to create directory structure: {e}")

def test_upnp_connection():
    """Test if UPnP is available and working"""
    global upnp_available, last_upnp_check
    try:
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        devices_discovered = upnp.discover()
        if devices_discovered > 0:
            upnp.selectigd()
            upnp_available = True
            last_upnp_check = datetime.now()
            logger.info(f"UPnP connection successful - {devices_discovered} device(s) discovered")
            return True, f"Connected to {devices_discovered} UPnP device(s)"
        else:
            upnp_available = False
            last_upnp_check = datetime.now()
            logger.warning("No UPnP devices discovered")
            return False, "No UPnP devices found"
    except Exception as e:
        upnp_available = False
        last_upnp_check = datetime.now()
        logger.error(f"UPnP connection failed: {e}")
        return False, f"UPnP error: {str(e)}"

def upnp_monitor():
    """Background thread to monitor UPnP connection and restore ports"""
    global upnp_available, port_restoration_enabled
    logger.info("UPnP monitor thread started")
    
    while True:
        try:
            # Check UPnP availability
            was_available = upnp_available
            is_available, message = test_upnp_connection()
            
            # If UPnP just became available and we have stored ports, restore them
            if is_available and not was_available and port_restoration_enabled:
                logger.info("UPnP connection restored, attempting to restore stored ports")
                try:
                    restore_stored_ports()
                except Exception as e:
                    logger.error(f"Failed to restore ports: {e}")
            
            # Sleep for 60 seconds before next check
            time.sleep(60)
            
        except Exception as e:
            logger.error(f"Error in UPnP monitor: {e}")
            time.sleep(30)  # Wait shorter time on error

def restore_stored_ports():
    """Restore ports from storage (improved version of open_stored_ports)"""
    try:
        port_mappings = load_ports()
        if not port_mappings:
            logger.info("No stored ports to restore")
            return
        
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        devices_discovered = upnp.discover()
        if devices_discovered == 0:
            logger.warning("Cannot restore ports - no UPnP devices discovered")
            return
        
        upnp.selectigd()
        restored_count = 0
        failed_count = 0
        
        for mapping in port_mappings:
            if 'external_port' in mapping and 'protocol' in mapping:
                port = mapping['external_port']
                protocol = mapping['protocol']
                internal_ip = mapping.get('internal_ip', '')
                if internal_ip == 'localhost':
                    internal_ip = upnp.lanaddr
                internal_port = mapping.get('internal_port', '')
                description = mapping.get('description', 'Restored Port')
                
                try:
                    result = upnp.addportmapping(port, protocol, internal_ip, internal_port, description, '')
                    if result:
                        restored_count += 1
                        logger.info(f"Restored port {port}/{protocol}")
                    else:
                        failed_count += 1
                        logger.warning(f"Failed to restore port {port}/{protocol} - mapping failed")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to restore port {port}/{protocol}: {e}")
            else:
                logger.warning("Invalid port mapping format in stored ports")
        
        logger.info(f"Port restoration complete: {restored_count} restored, {failed_count} failed")
        
    except Exception as e:
        logger.error(f"Failed to restore stored ports: {e}")

# Call this function before using files
ensure_directories_exist()

# Start UPnP monitoring in background thread
def start_upnp_monitor():
    global upnp_monitor_thread
    if upnp_monitor_thread is None or not upnp_monitor_thread.is_alive():
        upnp_monitor_thread = threading.Thread(target=upnp_monitor, daemon=True)
        upnp_monitor_thread.start()
        logger.info("UPnP monitor thread started")

@app.before_first_request
def initialize():
    logger.info("Initializing UPnP Port Manager")
    start_upnp_monitor()
    # Initial UPnP test and port restoration
    test_upnp_connection()
    try:
        restore_stored_ports()
    except Exception as e:
        logger.error(f"Failed initial port restoration: {e}")

def save_ports(port_mappings):
    """Save port mappings to file with error handling"""
    try:
        with open(PORTS_FILE, 'w') as f:
            json.dump(port_mappings, f, indent=4)
        logger.info(f"Saved {len(port_mappings)} port mappings to {PORTS_FILE}")
    except Exception as e:
        logger.error(f"Error saving ports to {PORTS_FILE}: {e}")
        raise

def load_ports():
    """Load port mappings from file with error handling"""
    try:
        if os.path.exists(PORTS_FILE):
            with open(PORTS_FILE, 'r') as f:
                ports = json.load(f)
                logger.debug(f"Loaded {len(ports)} port mappings from {PORTS_FILE}")
                return ports
        return []
    except Exception as e:
        logger.error(f"Error loading ports from {PORTS_FILE}: {e}")
        return []


def open_port(port, protocol, internal_ip, internal_port, description):
    """Open a port with improved error handling and validation"""
    try:
        # Validate inputs
        if not (1 <= port <= 65535):
            return False, "Port must be between 1 and 65535"
        if not (1 <= internal_port <= 65535):
            return False, "Internal port must be between 1 and 65535"
        if protocol not in ['TCP', 'UDP']:
            return False, "Protocol must be TCP or UDP"
        
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        devices_discovered = upnp.discover()
        if devices_discovered == 0:
            logger.warning("No UPnP devices discovered when attempting to open port")
            return False, "No UPnP devices discovered"
        
        try:
            upnp.selectigd()
        except Exception as e:
            logger.error(f"Error selecting IGD: {e}")
            return False, f"Error selecting IGD: {str(e)}"
        
        try:
            # Check if port is already mapped
            existing_mapping = upnp.getspecificportmapping(port, protocol)
            if existing_mapping[0]:
                logger.warning(f"Port {port}/{protocol} is already mapped to {existing_mapping[0]}:{existing_mapping[1]}")
                return False, f"Port {port}/{protocol} is already mapped"
            
            result = upnp.addportmapping(port, protocol, internal_ip, internal_port, description, '')
            if result:
                port_mappings = load_ports()
                if internal_ip == upnp.lanaddr:
                    internal_ip = 'localhost'
                new_mapping = {
                    'external_port': port,
                    'protocol': protocol,
                    'internal_ip': internal_ip,
                    'internal_port': internal_port,
                    'description': description,
                    'created_at': datetime.now().isoformat()
                }
                port_mappings.append(new_mapping)
                save_ports(port_mappings)
                logger.info(f"Successfully opened port {port}/{protocol} -> {internal_ip}:{internal_port}")
                return True, None
            else:
                logger.error(f"Failed to add port mapping for {port}/{protocol}")
                return False, "Failed to add port mapping"
        except Exception as e:
            error_message = f"Failed to open port {port}/{protocol}: {str(e)}"
            logger.error(error_message)
            return False, error_message
    except Exception as e:
        error_message = f"Error initializing UPnP: {str(e)}"
        logger.error(error_message)
        return False, error_message

def close_port(port, protocol):
    """Close a port with improved error handling"""
    try:
        if not (1 <= port <= 65535):
            return False, "Port must be between 1 and 65535"
        if protocol not in ['TCP', 'UDP']:
            return False, "Protocol must be TCP or UDP"
            
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        devices_discovered = upnp.discover()
        if devices_discovered == 0:
            logger.warning("No UPnP devices discovered when attempting to close port")
            return False, "No UPnP devices discovered"
        
        upnp.selectigd()
        
        logger.info(f"Closing port {port}/{protocol}...")
        result = upnp.deleteportmapping(port, protocol)

        # Update stored port mappings
        port_mappings = load_ports()
        original_count = len(port_mappings)
        updated_port_mappings = [p for p in port_mappings if p.get('external_port') != port or p.get('protocol') != protocol]
        save_ports(updated_port_mappings)
        
        if len(updated_port_mappings) < original_count:
            logger.info(f"Port {port}/{protocol} closed successfully and removed from storage")
        else:
            logger.info(f"Port {port}/{protocol} closed but was not found in storage")
            
        return True, None
    except Exception as e:
        error_message = f"Failed to close port {port}/{protocol}: {str(e)}"
        logger.error(error_message)
        return False, error_message


def close_ports(upnp, port_mappings):
    """Close multiple ports with improved error handling"""
    try:
        upnp.discoverdelay = 200
        devices_discovered = upnp.discover()
        if devices_discovered == 0:
            logger.warning("No UPnP devices discovered when attempting to close ports")
            return False
        
        upnp.selectigd()
        
        closed_count = 0
        failed_count = 0
        
        for mapping in port_mappings:
            port = mapping['external_port']
            protocol = mapping['protocol']
            try:
                upnp.deleteportmapping(port, protocol)
                closed_count += 1
                logger.info(f"Closed port {port}/{protocol}")
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to close port {port}/{protocol}: {e}")
        
        logger.info(f"Closed {closed_count} ports, {failed_count} failures")
        return True
    except Exception as e:
        logger.error(f"Failed to close ports: {e}")
        return False

def list_open_ports():
    """List currently open ports with improved error handling"""
    try:
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        devices_discovered = upnp.discover()
        if devices_discovered == 0:
            logger.warning("No UPnP devices discovered when listing ports")
            return []
        
        upnp.selectigd()
        ports = []
        i = 0
        while True:
            try:
                port_mapping = upnp.getgenericportmapping(i)
                if port_mapping is None:
                    break
                ports.append({
                    'external_port': port_mapping[0],
                    'protocol': port_mapping[1],
                    'internal_ip': port_mapping[2][0],
                    'internal_port': port_mapping[2][1],
                    'description': port_mapping[3]
                })
                i += 1
            except Exception as e:
                logger.error(f"Error reading port mapping {i}: {e}")
                break
                
        logger.debug(f"Listed {len(ports)} open ports")
        return ports
    except Exception as e:
        logger.error(f"Failed to list open ports: {e}")
        return []

@app.route('/')
def index():
    """Main page with improved error handling"""
    try:
        port_mappings = list_open_ports()
        return render_template('index.html', port_mappings=port_mappings)
    except Exception as e:
        logger.error(f"Error loading index page: {e}")
        flash('Error loading port information. Please check UPnP connection.', 'danger')
        return render_template('index.html', port_mappings=[])

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    global upnp_available, last_upnp_check
    
    try:
        # Force a fresh UPnP check if it's been more than 5 minutes
        if last_upnp_check is None or (datetime.now() - last_upnp_check).seconds > 300:
            test_upnp_connection()
        
        return jsonify({
            'status': 'healthy' if upnp_available else 'degraded',
            'upnp_available': upnp_available,
            'message': 'UPnP available' if upnp_available else 'UPnP unavailable',
            'last_check': last_upnp_check.isoformat() if last_upnp_check else None,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'unhealthy',
            'upnp_available': False,
            'message': f'Health check failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/open', methods=['POST'])
def open_port_route():
    """Open port route with improved validation and error handling"""
    try:
        external_port = int(request.form['external_port'])
        protocol = request.form['protocol']
        internal_ip = request.form['internal_ip']
        internal_port = int(request.form['internal_port'])
        description = request.form['description']
        
        # Additional validation
        if not description.strip():
            flash('Description cannot be empty', 'danger')
            return redirect(url_for('index'))
        
        # Validate IP address format
        try:
            socket.inet_aton(internal_ip)
        except socket.error:
            flash('Invalid IP address format', 'danger')
            return redirect(url_for('index'))
        
        success, error_message = open_port(external_port, protocol, internal_ip, internal_port, description)
        if success:
            flash(f'Port {external_port}/{protocol} opened successfully.', 'success')
            logger.info(f"Port {external_port}/{protocol} opened via web interface")
        else:
            flash(f'Failed to open port {external_port}/{protocol}. Error: {error_message}', 'danger')
    except ValueError as e:
        flash('Invalid port number format', 'danger')
        logger.error(f"Invalid port number in open_port_route: {e}")
    except Exception as e:
        flash(f'Unexpected error: {str(e)}', 'danger')
        logger.error(f"Unexpected error in open_port_route: {e}")
    
    return redirect(url_for('index'))

@app.route('/close', methods=['POST'])
def close_port_route():
    """Close port route with improved error handling"""
    try:
        port = int(request.form['port'])
        protocol = request.form['protocol']
        success, error_message = close_port(port, protocol)
        if success:
            flash(f'Port {port}/{protocol} closed successfully.', 'success')
            logger.info(f"Port {port}/{protocol} closed via web interface")
        else:
            flash(f'Failed to close port {port}/{protocol}. Error: {error_message}', 'danger')
    except ValueError as e:
        flash('Invalid port number format', 'danger')
        logger.error(f"Invalid port number in close_port_route: {e}")
    except Exception as e:
        flash(f'Unexpected error: {str(e)}', 'danger')
        logger.error(f"Unexpected error in close_port_route: {e}")
    
    return redirect(url_for('index'))

@app.route('/localip')
def get_local_ip():
    """Get local IP with improved error handling"""
    try:
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        devices_discovered = upnp.discover()
        if devices_discovered == 0:
            logger.warning("No UPnP devices discovered for local IP request")
            return "192.168.1.100", 404  # Default fallback
        upnp.selectigd()
        local_ip = upnp.lanaddr
        logger.debug(f"Retrieved local IP: {local_ip}")
        return local_ip
    except Exception as e:
        logger.error(f"Failed to get local IP: {e}")
        return "192.168.1.100", 500  # Default fallback

@app.route('/refresh_ports', methods=['POST'])
def refresh_ports():
    """Refresh ports with improved error handling and logging"""
    try:
        logger.info("Manual port refresh initiated")
        # Close all ports listed in ports.json
        port_mappings = load_ports()
        if port_mappings:
            upnp = miniupnpc.UPnP()
            close_success = close_ports(upnp, port_mappings)
            if not close_success:
                logger.warning("Some ports failed to close during refresh")

        # Open all ports listed in ports.json
        restore_stored_ports()

        flash('Ports refreshed successfully.', 'success')
        logger.info("Port refresh completed successfully")
    except Exception as e:
        error_msg = f"Failed to refresh ports: {e}"
        logger.error(error_msg)
        flash('Failed to refresh ports.', 'danger')

    return redirect(url_for('index'))

@app.route('/export', methods=['GET'])
def export_ports():
    """Export ports with improved error handling"""
    try:
        if not os.path.exists(PORTS_FILE):
            flash('No ports file found to export', 'danger')
            return redirect(url_for('index'))
        
        logger.info("Ports exported via web interface")
        return send_file(PORTS_FILE, as_attachment=True, download_name='ports.json')
    except Exception as e:
        error_msg = f'Failed to export ports: {str(e)}'
        logger.error(error_msg)
        flash(error_msg, 'danger')
        return redirect(url_for('index'))

@app.route('/import', methods=['POST'])
def import_ports():
    """Import ports with improved validation and error handling"""
    try:
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(url_for('index'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(url_for('index'))
        
        if not file.filename.endswith('.json'):
            flash('Invalid file type. Please upload a JSON file.', 'danger')
            return redirect(url_for('index'))
        
        try:
            filename = secure_filename(file.filename)
            file_content = file.read()
            imported_ports = json.loads(file_content)
            
            # Validate imported data structure
            if not isinstance(imported_ports, list):
                flash('Invalid file format. Expected a list of port mappings.', 'danger')
                return redirect(url_for('index'))
            
            # Validate each port mapping
            for port_mapping in imported_ports:
                if not isinstance(port_mapping, dict):
                    flash('Invalid port mapping format in file.', 'danger')
                    return redirect(url_for('index'))
                required_fields = ['external_port', 'protocol', 'internal_ip', 'internal_port', 'description']
                if not all(field in port_mapping for field in required_fields):
                    flash('Missing required fields in port mapping.', 'danger')
                    return redirect(url_for('index'))
            
            save_ports(imported_ports)
            restore_stored_ports()
            flash(f'Successfully imported and opened {len(imported_ports)} port mappings', 'success')
            logger.info(f"Imported {len(imported_ports)} port mappings from {filename}")
            
        except json.JSONDecodeError:
            flash('Invalid JSON file format.', 'danger')
        except Exception as e:
            error_msg = f'Failed to import ports: {str(e)}'
            logger.error(error_msg)
            flash(error_msg, 'danger')
    except Exception as e:
        error_msg = f'Unexpected error during import: {str(e)}'
        logger.error(error_msg)
        flash(error_msg, 'danger')
    
    return redirect(url_for('index'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404 error: {request.url}")
    return render_template('index.html', port_mappings=[]), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}")
    flash('An internal error occurred. Please try again.', 'danger')
    return render_template('index.html', port_mappings=[]), 500

# Graceful shutdown
import signal
import sys

def signal_handler(sig, frame):
    global upnp_monitor_thread
    logger.info("Shutting down UPnP Port Manager...")
    if upnp_monitor_thread and upnp_monitor_thread.is_alive():
        logger.info("Stopping UPnP monitor thread...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    logger.info(f"Starting UPnP Port Manager on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)