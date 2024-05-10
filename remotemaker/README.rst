Remote Map Generation Utility
=============================

*   Python script
*   Installed into GitHub workflow

    -   install Python
    -   install poetry
    -   checkout remotemaker repo.

*   run it wth params

    -   map's repo/manifest/commit
    -   server secret/Server URL

*   code

    -   started with above params
    -   send POST, get PID and status
    -   idle poll, checks, log/status

        -   print (to console) new log lines and status changes

    -   can we use python logger to show colour? (ERROR, INFO, CRITICAL, WARN)
    -   Exit with error if status error termination or after say 10 minutes
