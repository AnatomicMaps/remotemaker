# Remote Map Generation Utility

A Python tool to remotely run [mapmaker](https://github.com/AnatomicMaps/flatmap-maker).

## Installation

### Local system

Install the latest released wheel in a Python 3.12 environment, for instance with [uv](https://docs.astral.sh/uv/):


```
$ uv add https://github.com/AnatomicMaps/remotemaker/releases/download/v0.3.1/remotemaker-0.3.1-py3-none-any.whl
```

### GitHub workflow

-   install Python 3.12
-   install uv
-   checkout remotemaker repo
-   ...

## Running

First make sure the Python environment into which `remotemaker` has been installed is active.

```
$ remotemaker --help
```

### Parameters

-   map's repo/manifest/commit
-   server secret/Server URL

### Architecture

-   started with above params
-   send POST, get PID and status
-   idle poll, checks, log/status
    -   print (to console) new log lines and status changes
-   can we use python logger to show colour? (ERROR, INFO, CRITICAL, WARN)
-   Exit with error if status error termination or after say 10 minutes
