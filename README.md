# UPnP Port Manager

A production-ready Flask-based web application that allows users to manage port mappings on their router using UPnP (Universal Plug and Play). This project is designed to be run as a Docker container for easy deployment and management.

## 🚀 New Features (v2.0)

### Automatic Port Restoration
- **Background Monitoring**: Continuously monitors UPnP connection status
- **Auto-Recovery**: Automatically restores port mappings when connection is restored after interruption
- **Smart Restoration**: Only restores ports when coming back online, preventing unnecessary operations

### Improved User Interface
- **Responsive Design**: Works well on desktop and mobile devices
- **Scrollable Port List**: Handles large numbers of ports with a scrollable table
- **Sticky Controls**: Form controls remain visible while scrolling through ports
- **Real-time Status**: Connection status indicator with automatic updates
- **Better Validation**: Enhanced form validation with user-friendly error messages

### Production-Ready Features
- **Comprehensive Logging**: Structured logging to files and console
- **Health Check Endpoint**: `/health` endpoint for monitoring and load balancers
- **Error Handling**: Graceful error handling with detailed logging
- **Security**: Non-root container user and input validation
- **Performance**: Optimized for production with proper gunicorn configuration

## Features

- ✅ Open and close ports on your router
- ✅ View currently open ports with improved UI
- ✅ Import and export port mappings in JSON format
- ✅ Refresh ports to synchronize with the current router settings
- ✅ **NEW**: Automatic port restoration when connection is lost and restored
- ✅ **NEW**: Responsive design that works with many ports
- ✅ **NEW**: Real-time connection status monitoring
- ✅ **NEW**: Production-ready logging and monitoring
- ✅ **NEW**: Health check endpoint for monitoring

## Prerequisites

- Docker
- Docker Compose
- Router with UPnP enabled
- Network with host mode access (for UPnP discovery)

## Getting Started

### Option 1: Use Pre-built Docker Image (Recommended)

The Docker image is automatically built and published to GitHub Container Registry on every push to main.

```bash
# Pull the latest image
docker pull ghcr.io/maximocitba/upnp-manager:latest

# Run with host networking (required for UPnP discovery)
docker run -d \
  --name upnp-manager \
  --network host \
  -e PORT=56133 \
  -e SECRET_KEY=your-super-secret-key-here \
  -v upnp-ports:/usr/src/app/ports_data \
  -v upnp-logs:/usr/src/app/logs \
  ghcr.io/maximocitba/upnp-manager:latest
```

### Option 2: Build from Source

#### Clone the Repository

```bash
git clone https://github.com/maximocitba/upnp-manager.git
cd upnp-manager
```

### Configure Environment

1. **Edit docker-compose.yml** to set your environment variables:

```yml
environment:
  - PORT=56133
  - SECRET_KEY=your-super-secret-production-key-here  # IMPORTANT: Change this!
  - FLASK_ENV=production
```

⚠️ **Security Warning**: Always change the `SECRET_KEY` in production!

### Build and Run

```bash
# Build and start the container
docker-compose up --build -d

# View logs
docker-compose logs -f upnp-manager
```

### Access the Application

Once the container is running, access the application at:
- **Web Interface**: `http://localhost:56133`
- **Health Check**: `http://localhost:56133/health`

## 🔧 API Endpoints

### Web Interface
- `GET /` - Main application interface
- `POST /open` - Open a new port mapping
- `POST /close` - Close an existing port mapping
- `POST /refresh_ports` - Refresh all port mappings
- `GET /export` - Export port mappings as JSON
- `POST /import` - Import port mappings from JSON

### Monitoring
- `GET /health` - Health check endpoint (returns JSON status)
- `GET /localip` - Get local IP address

## 📊 Monitoring and Logging

### Health Check Response
```json
{
  "status": "healthy",
  "upnp_available": true,
  "message": "UPnP available",
  "last_check": "2023-12-01T12:00:00",
  "timestamp": "2023-12-01T12:00:00"
}
```

### Log Files
- Application logs: `/usr/src/app/logs/upnp-manager.log`
- Access logs: stdout (captured by Docker)
- Error logs: stderr (captured by Docker)

### Docker Health Check
The container includes a built-in health check that monitors the application every 30 seconds.

```bash
# Check container health
docker ps
# Look for (healthy) status

# View health check logs
docker inspect upnp-manager | grep -A 10 Health
```

## 🔒 Security Features

- **Non-root execution**: Container runs as non-root user
- **Input validation**: All user inputs are validated
- **Secure file handling**: Safe filename handling for imports
- **Error boundary**: Graceful error handling prevents crashes
- **Log sanitization**: Sensitive data not logged

## 🐛 Troubleshooting

### UPnP Connection Issues
1. Ensure UPnP is enabled on your router
2. Check that the container has `network_mode: host`
3. Verify firewall isn't blocking UPnP discovery
4. Check logs: `docker-compose logs upnp-manager`

### Port Restoration Not Working
1. Check the health endpoint: `curl http://localhost:56133/health`
2. Verify ports are saved in storage: check the exports
3. Review logs for restoration attempts
4. Manually refresh ports if needed

### Performance Issues
1. Monitor container resources: `docker stats upnp-manager`
2. Check log file sizes in `/usr/src/app/logs/`
3. Consider log rotation if files grow large
4. Reduce UPnP discovery delay if needed

## 📈 Production Deployment

### Environment Variables
- `PORT`: Application port (default: 5000)
- `SECRET_KEY`: Flask secret key (required for production)
- `FLASK_ENV`: Set to "production" for production deployment

### Reverse Proxy Example (nginx)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:56133;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /health {
        proxy_pass http://localhost:56133/health;
        access_log off;
    }
}
```

### Log Rotation
```bash
# Add to crontab for log rotation
0 2 * * * docker exec upnp-manager find /usr/src/app/logs -name "*.log" -size +50M -delete
```

## 📝 Usage Examples

### Opening a Port
1. Fill in the port form:
   - External Port: 8080
   - Protocol: TCP
   - Internal IP: 192.168.1.100
   - Internal Port: 8080
   - Description: "Web Server"
2. Click "Open Port"

### Bulk Import/Export
1. Export current ports: Click "Export Ports"
2. Edit the JSON file as needed
3. Import updated ports: Click "Import Ports" and select your file

### Monitoring
```bash
# Check health status
curl http://localhost:56133/health | jq

# Monitor logs in real-time
docker-compose logs -f upnp-manager

# Check container health
docker ps
```

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes with proper logging and error handling
4. Test thoroughly, especially UPnP edge cases
5. Submit a pull request

### Development Setup
```bash
# Clone and install dependencies
git clone https://github.com/maximocitba/upnp-manager.git
cd upnp-manager
pip install -r requirements.txt

# Run in development mode
export FLASK_ENV=development
export SECRET_KEY=dev-secret-key
python app.py
```

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🔄 Changelog

### v2.0.0
- ✅ Added automatic port restoration with background monitoring
- ✅ Improved UI with scrollable tables and responsive design
- ✅ Production-ready logging and error handling
- ✅ Health check endpoint for monitoring
- ✅ Enhanced security with non-root container execution
- ✅ Better validation and user feedback
- ✅ Comprehensive documentation and troubleshooting guides
- ✅ **NEW**: CI/CD pipeline for automated Docker image publishing

### v1.0.0
- ✅ Basic UPnP port management functionality
- ✅ Web interface for port operations
- ✅ Import/export capabilities
- ✅ Docker containerization
