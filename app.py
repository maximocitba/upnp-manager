import os
import json
import miniupnpc
import socket
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__) 
app.secret_key = os.environ.get('SECRET_KEY')
PORTS_FILE = '/usr/src/app/ports_data/ports.json'

PORT = int(os.environ.get('PORT', 5000))

def ensure_ports_file_exists():
    try:
        os.makedirs(os.path.dirname(PORTS_FILE), exist_ok=True)
        if not os.path.exists(PORTS_FILE):
            with open(PORTS_FILE, 'w') as f:
                json.dump([], f)
    except Exception as e:
        print(f"Warning: Failed to create or access ports.json: {e}")

# Call this function before using PORTS_FILE
ensure_ports_file_exists()

@app.before_first_request
def initialize():
    print("Initializing UPnP Port Manager")
    open_stored_ports()

def save_ports(port_mappings):
    try:
        with open(PORTS_FILE, 'w') as f:
            json.dump(port_mappings, f, indent=4)
        print(f"Saved {len(port_mappings)} port mappings to {PORTS_FILE}")
    except Exception as e:
        print(f"Error saving ports to {PORTS_FILE}: {e}")

def load_ports():
    if os.path.exists(PORTS_FILE):
        with open(PORTS_FILE, 'r') as f:
            return json.load(f)
    return []

def open_stored_ports():
    try:
        port_mappings = load_ports()
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        upnp.discover()
        upnp.selectigd()
        
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
                    upnp.addportmapping(port, protocol, internal_ip, internal_port, description, '')
                except Exception as e:
                    print(f"Failed to restore port {port}/{protocol}: {e}")
            else:
                print("Invalid port mapping format in ports.json")

    except Exception as e:
        print(f"Failed to open stored ports: {e}")

def open_port(port, protocol, internal_ip, internal_port, description):
    try:
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        devices_discovered = upnp.discover()
        if devices_discovered == 0:
            return False, "No UPnP devices discovered"
        
        try:
            upnp.selectigd()
        except Exception as e:
            return False, f"Error selecting IGD: {str(e)}"
        
        try:
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
                    'description': description
                }
                port_mappings.append(new_mapping)
                save_ports(port_mappings)
                print(f"Added new port mapping: {new_mapping}")
                return True, None
            else:
                return False, "Failed to add port mapping"
        except Exception as e:
            error_message = f"Failed to open port {port}/{protocol}: {str(e)}"
            print(error_message)
            print(f"Exception details: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, error_message
    except Exception as e:
        error_message = f"Error initializing UPnP: {str(e)}"
        print(error_message)
        return False, error_message

def close_port(port, protocol):
    try:
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        upnp.discover()
        upnp.selectigd()
        
        print(f"Closing port {port}/{protocol}...")
        upnp.deleteportmapping(port, protocol)

        port_mappings = load_ports()
        updated_port_mappings = [p for p in port_mappings if p.get('external_port') != port or p.get('protocol') != protocol]
        save_ports(updated_port_mappings)
        
        print(f"Port {port}/{protocol} closed successfully.")
        return True, None
    except Exception as e:
        error_message = f"Failed to close port {port}/{protocol}: {str(e)}"
        print(error_message)
        return False, error_message


def close_ports(upnp, port_mappings):
    try:
        upnp.discoverdelay = 200
        upnp.discover()
        upnp.selectigd()
        
        for mapping in port_mappings:
            port = mapping['external_port']
            protocol = mapping['protocol']
            upnp.deleteportmapping(port, protocol)
        return True
    except Exception as e:
        print(f"Failed to close ports: {e}")
        return False


def list_open_ports():
    try:
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        upnp.discover()
        upnp.selectigd()
        ports = []
        i = 0
        while True:
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
        return ports
    except Exception as e:
        print(f"Failed to list open ports: {e}")
        return []

@app.route('/')
def index():
    port_mappings = list_open_ports()
    return render_template('index.html', port_mappings=port_mappings)

@app.route('/open', methods=['POST'])
def open_port_route():
    external_port = int(request.form['external_port'])
    protocol = request.form['protocol']
    internal_ip = request.form['internal_ip']
    internal_port = int(request.form['internal_port'])
    description = request.form['description']
    success, error_message = open_port(external_port, protocol, internal_ip, internal_port, description)
    if success:
        flash(f'Port {external_port}/{protocol} opened successfully.', 'success')
    else:
        flash(f'Failed to open port {external_port}/{protocol}. Error: {error_message}', 'danger')
    return redirect(url_for('index'))

@app.route('/close', methods=['POST'])
def close_port_route():
    port = int(request.form['port'])
    protocol = request.form['protocol']
    success, error_message = close_port(port, protocol)
    if success:
        flash(f'Port {port}/{protocol} closed successfully.', 'success')
    else:
        flash(f'Failed to close port {port}/{protocol}. Error: {error_message}', 'danger')
    return redirect(url_for('index'))

@app.route('/localip')
def get_local_ip():
    upnp = miniupnpc.UPnP()
    upnp.discoverdelay = 200
    upnp.discover()
    upnp.selectigd()
    return upnp.lanaddr

@app.route('/refresh_ports', methods=['POST'])
def refresh_ports():
    try:
        # Close all ports listed in ports.json
        port_mappings = load_ports()
        upnp = miniupnpc.UPnP()
        close_ports(upnp, port_mappings)

        # Open all ports listed in ports.json
        open_stored_ports()

        flash('Ports refreshed successfully.', 'success')
    except Exception as e:
        print(f"Failed to refresh ports: {e}")
        flash('Failed to refresh ports.', 'danger')

    return redirect(url_for('index'))

@app.route('/export', methods=['GET'])
def export_ports():
    try:
        return send_file(PORTS_FILE, as_attachment=True, download_name='ports.json')
    except Exception as e:
        flash(f'Failed to export ports: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/import', methods=['POST'])
def import_ports():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('index'))
    if file and file.filename.endswith('.json'):
        try:
            filename = secure_filename(file.filename)
            file_content = file.read()
            imported_ports = json.loads(file_content)
            save_ports(imported_ports)
            open_stored_ports()
            flash('Ports imported and opened successfully', 'success')
        except Exception as e:
            flash(f'Failed to import ports: {str(e)}', 'danger')
    else:
        flash('Invalid file type. Please upload a JSON file.', 'danger')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)