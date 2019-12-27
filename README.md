# VCU UI

VCU Pro minimal Web UI displays useful status information and allows maintenance actions.

The UI is built on top of the Bottle Python webserver. 


## Installation

Install Bottle 

```bash
pip3 install bottle
```

Copy the run script `vcu-ui` to `/usr/bin` and make it executable

```bash
cp vcu-ui /usr/bin/vcu-ui
chmod +x /usr/bin/vcu-ui
```

Copy the service ```vcu-ui.service``` file to ```/usr/lib/systemd/system/vcu-ui.service```.

```bash
cp vcu-ui.service /usr/lib/systemd/system/vcu-ui.service
```

```bash
systemctl daemon-reload     # Tell systemd to search for new services
systemctl enable vcu-ui     # Enable service for next startup

systemctl start vcu-ui      # Start service right now
```
