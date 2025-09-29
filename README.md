# MeshCore Web Client

A modern web-based client for MeshCore communication, built with Python and Flask.

## Features

- Modern web interface for MeshCore communication
- Support for both public and private messaging
- Message path tracking
- SQLite database for message storage
- Paginated message display
- Docker support for easy deployment

## Project Structure

```tree
meshcore-base/
├── docs/               # Documentation files
├── src/               # Source code
│   ├── static/        # Static files (CSS, JS, images)
│   ├── templates/     # HTML templates
│   └── database/      # Database models and migrations
├── Dockerfile         # Docker configuration
├── requirements.txt   # Python dependencies
└── pyproject.toml    # Poetry configuration
```

## Development Setup

1. Clone the repository

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   or with Poetry:

   ```bash
   poetry install
   ```

3. Run the development server:

   ```bash
   flask run --port 3000
   ```

## Docker Deployment

Build the Docker image:

```bash
docker build -t meshcore-web .
```

Run the container:

```bash
docker run -p 3000:3000 -v /dev/ttyUSB1:/dev/ttyUSB1 --device=/dev/ttyUSB1 meshcore-web
```

## References

Python MeshCore Library: [meshcore-py](https://github.com/meshcore-dev/meshcore_py)