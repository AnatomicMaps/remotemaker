# Remote Map Generation Utility

A Python tool to remotely run [mapmaker](https://github.com/AnatomicMaps/flatmap-maker).

## Installation


### GitHub workflow

-   install Python
-   install uv
-   checkout remotemaker repo.
-   ...

## Running

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
