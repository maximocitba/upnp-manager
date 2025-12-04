# UPnP Port Manager - AI Coding Instructions

## Project Overview
This is a Flask-based web application for managing UPnP port mappings on routers. It is designed for Docker deployment using host networking to enable SSDP discovery.

## Architecture & Core Components
- **Backend**: Flask (`app.py`) handles HTTP requests and application logic.
- **UPnP Integration**: Uses `miniupnpc` library to communicate with routers.
  - **Critical**: Requires `network_mode: host` in Docker to function correctly.
- **Data Persistence**: Simple JSON storage in `ports_data/ports.json`.
- **Background Monitoring**: A dedicated thread (`upnp_monitor` in `app.py`) checks connection status and handles auto-restoration of ports.
- **Frontend**: Server-side rendered templates (`templates/`) with static assets (`static/`).

## Critical Workflows

### Development
- **Start Local Dev**: Run `./dev-start.sh`. This sets up the venv and runs the Flask dev server.
- **Docker Build**: `docker build -t upnp-manager .`
- **Docker Run**: Must use host networking:
  ```bash
  docker run --network host -e PORT=56133 ... upnp-manager
  ```

### System Dependencies
- The `Dockerfile` installs `libminiupnpc-dev`. This system library is required for the python `miniupnpc` package.

## Code Patterns & Conventions

### UPnP Interaction
- **Discovery**: Always use `upnp.discover()` with a delay (e.g., 200ms) before selecting an IGD.
- **Error Handling**: Wrap UPnP calls in try/except blocks. UPnP operations are network-dependent and prone to timeouts or failures.
- **Thread Safety**: The `upnp_monitor` runs concurrently. Ensure shared state (like `upnp_available`) is managed carefully.

### Flask & Web
- **Routes**: Defined in `app.py`.
- **Health Check**: Maintain the `/health` endpoint for Docker healthchecks.
- **Security**: 
  - Use `secure_filename` when handling file inputs.
  - Run as non-root user in Docker (`upnpuser`).

### Logging
- Use the configured `logger` object.
- Logs are written to both console (stdout) and file (`logs/upnp-manager.log`).

## Key Files
- `app.py`: Main application logic, routes, and background thread.
- `wsgi.py`: Entry point for Gunicorn in production.
- `ports_data/ports.json`: Source of truth for persistent port mappings.
- `dev-start.sh`: Development bootstrap script.
