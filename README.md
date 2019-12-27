# VCU UI

A minimal Web user interface for VCU Pro based on bottle. It displays useful status information and allows maintenance actions.


## Run from Python

```python
import vcuui

vcuui.run_server(port=888)
```

## Run from Shell

The following start script is automatically created when this package is installed.

```bash
vcu-ui-start
```


## Installation as systemd service

Create the following service file ```vcu-ui.service``` in ```/usr/lib/systemd/system/vcu-ui.service```.

```
[Unit]
Description=VCU Pro Minimal WebUI
 
[Service]
Type=simple
ExecStart=/usr/bin/vcu-ui-start
PIDFile=/var/run/vcu-ui.pid
 
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=10
 
[Install]
WantedBy=multi-user.target
```

Manage the service with the following systemd commands.

```bash
systemctl daemon-reload     # Tell systemd to search for new services
systemctl enable vcu-ui     # Enable service for next startup

systemctl start vcu-ui      # Start service right now
```
