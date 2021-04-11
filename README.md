## NG800/VCU Pro User Interface

![System](https://img.shields.io/badge/system-VCU%20Pro-blue)
![System](https://img.shields.io/badge/system-NG800-blue)


### Introduction

A minimal Web user interface for the NG800/VCU Pro automotive gateway. It displays important status information and allows basic maintenance actions. Written in Python, based on Tornado webserver.


### Features

* Display important system information
  * System date/time, load, temperature, input voltage
  * Mobile link information: registration state, signal strength, bearer information
  * GNSS fix mode, position and speed
* Determine GSM cell location, including geographic position (uses OpenCellId and OpenStreetMap)
* Execute test ping over mobile network and display latency
* Upload of telemetry to Thingsboard server
* GNSS detailled information and automotive configuration
* Realtime driving display with speed and navigations information, live update


### Short Description

#### Main Page

The following is the main page, showing most information. To refresh information, reload the page. The slider, next to the Refresh Page button, can be enabled for automatic page refresh.

![Info](https://github.com/renestraub/vcu-ui/raw/master/preview/info.png)


#### GNSS Page

The GNSS page displays information about the GNSS module and allows configuration of some UDR relevant settings. Since the page has to load a lot of GNSS modem information, it takes 1..2 seconds to load. Refresh page manually to update live data or after a configuration change.

![Gnss](https://github.com/renestraub/vcu-ui/raw/master/preview/gnss.png)


#### Realtime Display

For drive tests the realtime page is most suitable. It display drive related information in realtime. The page is updated via a Websocket connection once a second. Check the green dot to see whether the connection to the VCU UI webserver is active. The dot blinks once a seconds to signal activity.

![Gnss](https://github.com/renestraub/vcu-ui/raw/master/preview/realtime.png)



### Requirements

* NG800/VCU Pro Hardware with developer image installed
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

Create the following service file ```vcu-ui.service``` in ```/usr/lib/systemd/system/```.  You can use the following command to invoke the system editor.

```
systemctl edit --full --force vcu-ui
```


The service file is also available on [Github](https://github.com/renestraub/vcu-ui/blob/master/vcu-ui.service)


```
[Unit]
Description=VCU Pro Minimal WebUI
After=gnss-mgr.service

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


### Revision History

#### v0.5.4 (20210411)

- Change IMU angles order to Yaw, Pitch, Roll
- Add Network traffic (wwan0, wlan0) query and Thingsboard upload
- Add ubxlib version and UBX protocol version report
- Update to ubxlib version 0.3.5
- Fix problem with GNSS page load/refresh


#### v0.5.3 (20210109)

- Add NG800
- Add disc information (eMMC wear level, root/data partition usage)
- Provide web app manifest to run as app
- Flake8 Python Linting


#### v0.5.2 (20200904)

- Wait for gpsd service to become ready at startup
- Supress minor position changes on cloud upload to save data volume


#### v0.5.0 (20200718)

- Major refactoring of Thingsboard IoT upload
- New transmit queue class


#### v0.4.4 (20200716)

- GNSS lever arm configuration added
- Upgrade to ubxlib 0.1.11 for lever arm


#### v0.4.2 (20200612)

- Updated this documentation
- Report RSRQ, ECIO as dB (not dBm)
- Report bearer info to Thingsboard
- Report UI version to Thingsboard
- Restart ping process after mobile link loss
- Queue telemetry data on upload error to retry later
- GNSS configuration save/reset added
- GNSS state save/clear (save-on-shutdown) added
- System reboot function added
- JavaScript code refactored
- General code cleanup, remove dead code
- Upgrade to ubxlib 0.1.9


#### Known Bugs & Limitations

- Thread safety issue when getting ESF status for GNSS. Leads to occasional page loading error.
- Rarely data is not sent to cloud. It is lost, since transmit queue is cleared.
