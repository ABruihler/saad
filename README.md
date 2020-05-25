# LosCat (aka SAAD)

A code monitoring tool being developed by students at Carleton College.

Additional documentation can be found under [/documentation/](./documentation/):

- [Background](./documentation/background.md)
- [Grammar Fuzzer](./documentation/grammar_fuzzer.md)
- [IDE Plugin](./documentation/ide_plugin.md)
- [Probe Walkthrough](./documentation/probe_walkthrough.md)
- [Python Code Finder](./documentation/python_code_finder.md)
- [Website](./documentation/website.md)

You can also check out the project website [here](https://skimberk.github.io/saad/). The code for this website is in [docs/](./docs/) and is hosted by Github (hence why it has the rather unfortunate name "docs").

## Getting Started

First, create virtual environment for installing dependencies:
```
$ python3 -m venv env
```

Then, activate the virtual environment. You will do this whenever you start working on the project:
```
$ source env/bin/activate
```

To install dependencies:
```
$ python3 -m pip install -r requirements.txt
```

To leave the virtual environment:
```
$ deactivate
```

## Config

The LosCat server reads in options from a config file. By default this is SAAD\_config.cfg, but it can be specified with the --master\_config argument when starting the server. The config has the following sections:
* Allowed Repos: a whitelist of repositories that are allowed to push to the server
* Local: Paths containing modules, probes, and configs on the server itself
* Repo: Default paths to look for probes, modules and configs within a monitored repo

Additionally, any section with the same name as an allowed repository will override the default settings for that repository.

Repositories may also have configs, although the only section allowed is [Local], which refers to folders and files in the repository itself. In addition, any config field set to false in the server config is disabled in the monitored Repo.

## Testing Locally

### Making a fake Github webhook request

Start the server then run the following command in your terminal (in the `saad` directory):
```
$ curl --header "Content-Type: application/json" \
    --request POST \
    --data-binary "@sample_webhook_request.json" \
    http://localhost:8080/run
```

## Setting up Server

Command for connecting to server:
```
$ ssh -i /Users/skimberk1/Downloads/comps-project-aws.pem ec2-user@ec2-52-14-246-137.us-east-2.compute.amazonaws.com
```

Print service logs (same as what you get by visiting `/logs`):
```
$ journalctl -n 500 --no-pager -u saad_python_service.service
```

Used this tutorial for setting up a service:
<https://github.com/torfsen/python-systemd-tutorial>

Used this documentation for forwarding port 80 to 8080:
<https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/7/html/security_guide/sec-port_forwarding>

Commands used to set up server:
```
$ sudo firewalld
$ sudo firewall-cmd --add-forward-port=port=80:proto=tcp:toport=8080
$ sudo firewall-cmd --runtime-to-permanent
$ sudo firewall-cmd --list-all

$ sudo useradd -r -s /bin/false saad_python_service

$ sudo systemctl enable /home/saad_python_service/saad/saad_python_service.service
$ sudo systemctl start saad_python_service
```

To update server code and restart service:
```
$ cd /home/saad_python_service/saad/
$ sudo -u saad_python_service git pull
$ sudo systemctl daemon-reload
$ sudo systemctl restart saad_python_service
```

To install Python (from source, since `yum` didn't have 3.8):
```
$ sudo yum install libffi-devel # Necessary to install psutils (fixes _ctypes error)
$ sudo yum install sqlite-devel # Necessary to have sqlite in Python
$ sudo yum install openssl-devel
$ cd /home/ec2-user/Python-3.8.1/
$ sudo ./configure --enable-optimizations
$ sudo make install
```
