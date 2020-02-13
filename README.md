# saad
A code monitoring tool being developed by students at Carleton College.

## Getting Started
First, create virtual environment for installing dependencies:

```
python3 -m venv env
```

Then, activate the virtual environment. You will do this whenever you start working on the project:

```
source env/bin/activate
```

To install dependencies:

```
python3 -m pip install -r requirements.txt
```


To leave the virtual environment:

```
deactivate
```


Used this tutorial for setting up a service:
<https://github.com/torfsen/python-systemd-tutorial>

Used this documentation for forwarding port 80 to 8080:
<https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/7/html/security_guide/sec-port_forwarding>

Commands used to set up server:

```
sudo firewalld
sudo firewall-cmd --add-forward-port=port=80:proto=tcp:toport=8080
sudo firewall-cmd --runtime-to-permanent
sudo firewall-cmd --list-all

sudo useradd -r -s /bin/false saad_python_service

sudo systemctl enable /home/saad_python_service/saad/saad_python_service.service
sudo systemctl start saad_python_service
```

To update server code and restart service:

```
cd /home/saad_python_service/saad/
sudo -u saad_python_service git pull
sudo systemctl daemon-reload
sudo systemctl restart saad_python_service
```
