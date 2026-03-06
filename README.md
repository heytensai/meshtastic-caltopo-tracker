# meshtastic-caltopo-tracker
Bridge between a Meshtastic node and a CalTopo tracker

# Install

- Make a copy of `default_config.yaml` named `config.yaml`.
- Create an access key in CalTopo. Set the access key in the `caltopo_url` variable in `config.yaml`.
- Set the `rate_limit` value in seconds for how often to update the CalTopo map.
- Run `listener.py`.
