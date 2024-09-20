# UPnP Port Manager

UPnP Port Manager is a Flask-based web application that allows users to manage port mappings on their router using UPnP (Universal Plug and Play). This project is designed to be run as a Docker container for easy deployment and management.

## Features

- Open and close ports on your router.
- View currently open ports.
- Import and export port mappings in JSON format.
- Refresh ports to synchronize with the current router settings.

## Prerequisites

- Docker
- Docker Compose

## Getting Started

### Clone the Repository

```bash
git clone https://github.com/your-username/upnp-port-manager.git
cd upnp-port-manager
```


### Build and Run the Docker Container

1. **Set up environment variables**: Edit docker-compose.yml file to set the PORT and SECRET_KEY variables.

```yml
SECRET_KEY=your_secret_key_herere
PORT=56133
```

2. **Build the Docker Image**:

```bash
docker-compose up --build
```


### Access the Application

Once the container is running, you can access the application by navigating to `http://localhost:56132` in your web browser.

## Usage

- **Open Port**: Enter the external port, protocol (TCP/UDP), internal IP, internal port, and a description to open a port.
- **Close Port**: Select a port to close it.
- **Refresh Ports**: Refresh the list of ports to sync with the router.
- **Import/Export Ports**: Manage your port mappings by importing from or exporting to a JSON file.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
