## VCU Pro User Interface

![System](https://img.shields.io/badge/system-VCU%20Pro-blue)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/vcu-ui)
![PyPI](https://img.shields.io/pypi/v/vcu-ui)
[![Build Status](https://www.travis-ci.org/renestraub/vcu-ui.svg?branch=master)](https://www.travis-ci.org/renestraub/vcu-ui)


### Introduction

A minimal Web user interface for the VCU Pro automotive gateway. It displays important status information and allows basic maintenance actions. Written in python, based on bottle webserver.


### Features

* Display of most important system information
  * System date/time, load, temperature
  * Mobile link information (registration state, signal strength, bearer information)
* Determine GSM cell location, including geographic position (uses OpenCellId and OpenStreetMap)
* Execute test ping over mobile network
* Create TCP service for u-Center GNSS tool
* Restart GSM modem
* Restart system (not yet implemented)


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
from vcuui.server import run_server

run_server(port=80)
```


#### Installation as systemd service

Create the following service file ```vcu-ui.service``` in ```/usr/lib/systemd/system/vcu-ui.service```. The service file is also available on ![Github](https://github.com/renestraub/vcu-ui/blob/master/vcu-ui.service)


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




