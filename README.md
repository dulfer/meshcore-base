# MeshCore Web Client

A web-based client for MeshCore communication, built with Python and Flask. Requires a MeshCore Companion Radio USB connected to the host, or passed through to the docker container.  

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
└── pyproject.toml    # Poetry project configuration
```

## Development Setup

1. Clone the repository

2. Install Poetry if you haven't already:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

4. Activate the Poetry shell:
   ```bash
   poetry shell
   ```

5. Run the development server:

   ```bash
   python src/run.py
   ```

   Or using Flask directly:

   ```bash
   FLASK_APP=meshcore_web.app flask run --port 3000
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