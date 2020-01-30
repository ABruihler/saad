# saad
A code monitoring tool being developed by students at Carleton College.

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
