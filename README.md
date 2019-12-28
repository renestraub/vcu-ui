## VCU UI

### Introduction

A minimal Web user interface for VCU Pro based on bottle. It displays important status information and allows basic maintenance actions. Written in python, based on bottle webserver.


### Features

* Display of most important system information
* Restart of GSM modem



### Preview

![Info](https://github.com/renestraub/vcu-ui/raw/master/preview/info.png)


### Requirements

* VCU Pro Hardware with developer image installed
* Python 3.7+



### Quickstart

1. Install the module with `pip install vcu-ui`
1. Start webserver from shell `vcu-ui-start`
1. Open the website with your browser `10.42.0.1`


#### Run from Python

```python
import vcuui

vcuui.run_server(port=888)
```


#### Installation as systemd service

Create the following service file ```vcu-ui.service``` in ```/usr/lib/systemd/system/vcu-ui.service```.

```
[Unit]
Description=VCU Pro Minimal WebUI
 
[Service]
Type=simple
ExecStart=/usr/bin/vcu-ui-start
PIDFile=/run/vcu-ui.pid
 
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

### Tips

* Check ...

