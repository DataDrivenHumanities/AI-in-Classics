# Setting up local Development

select one of the following options to setup your local development.

We Recommend using [Docker](#3running-with-docker-using-make)

## 1. Using the Build script

run the folloing command in your main directory:

```sh
sh .buld.sh
```

the cd into app folder and run:

```bash
python3 app.py
```

## 2. Using Poetry/Make

### Prerequisites for Poetry/Make

- Install Poetry `pip install poetry` on your system
- Make (Preinstalled on Mac & Linux) (if Windows try `pacman -S make`)
  - Confirm make `make --version`

In the main directory run:

```bash
make setup
```

Once installed run the following command:

```bash
make web
or 
make run
```

## 3.Running with Docker using Make

This project provides a simple Docker workflow for local development and testing.

### Prerequisites for Docker

- Install [Docker](https://docs.docker.com/get-docker/) on your system

### Build the Image & Run

From the project root:

```bash
make docker
```

## Other Commands

Stop containers:

```bash
docker stop <container_id>
```

Remove dangling images/containers:

```bash
docker system prune -f
```

adding Hot-Reload

```bash
docker run --rm -it \
  -p 8000:8000 \
  -v $(pwd):/app \
  classics-ai-app
```

## Common Issues

### Make Setup

#### `ModuleNotFoundError: No module named 'altair.vegalite.v4'`

Ensure you had altair installed, if not try running:

```bash
poetry add "altair<5,>=4.2"
```

This could be because you dont have graphviz system tool installed try downloading the following:

- macOS: `brew install graphviz`
- Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y graphviz`

