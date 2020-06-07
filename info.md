# HomeAssistant Hekr Devices Integration
[![GitHub Page](https://img.shields.io/badge/GitHub-alryaz%2Fhass--mosenergosbyt-blue)](https://github.com/alryaz/hass-mosenergosbyt)
[![Donate Yandex](https://img.shields.io/badge/Donate-Yandex-red.svg)](https://money.yandex.ru/to/410012369233217)
[![Donate PayPal](https://img.shields.io/badge/Donate-Paypal-blueviolet.svg)](https://www.paypal.me/alryaz)
{% set mainline_ver = 'v0.1.0' %}{% set mainline_num_ver = mainline_ver.replace("v", "").replace(".", "") | int %}{%- set features = {
    'v0.1.0': 'Multiple accounts support, GUI configuration',
}-%}{%- set breaking_changes = {} -%}
{% if installed %}{% if version_installed == "master" %}
#### ⚠ You are using development version
This branch may be unstable, as it contains commits not tested beforehand.  
Please, do not use this branch in production environments.
{% else %}{% set num_ver = version_installed.replace("v", "").replace(".","") | int %}{% if num_ver == mainline_num_ver %}
#### ✔ You are using mainline version{% else %}
#### 🚨 You are using an outdated release of Hekr component{% if num_ver < 20 %}
{% set print_header = True %}{% for ver, changes in breaking_changes.items() %}{% set ver = ver.replace("v", "").replace(".","") | int %}{% if num_ver < ver %}{% if print_header %}
##### Breaking changes (`{{ version_installed }}` -> `{{ mainline_ver }}`){% set print_header = False %}{% endif %}{% for change in changes %}
{{ '- '+change.pop(0) }}{% for changeline in change %}
{{ '  '+changeline }}{% endfor %}{% endfor %}{% endif %}{% endfor %}
{% endif %}{% endif %}
##### Features{% for ver, text in features.items() %}{% set feature_ver = ver.replace("v", "").replace(".", "") | int %}
- {% if num_ver < feature_ver %}**{% endif %}`{{ ver }}` {% if num_ver < feature_ver %}NEW** {% endif %}{{ text }}{% endfor %}

Please, report all issues to the [project's GitHub issues](https://github.com/alryaz/hass-hekr-component/issues).
{% endif %}{% else %}
## Features{% for ver, text in features.items() %}
- {{ text }} _(supported since `{{ ver }}`)_{% endfor %}
{% endif %}
## Screenshots
#### Account sensor
![Account sensor](https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/account.png)
#### Meter sensor
![Account sensor](https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/meter.png)

## Configuration
### Basic configuration example
```yaml
mosenergosbyt:
  username: !secret mosenergosbyt_username
  password: !secret mosenergosbyt_password
```

### Multiple users
```yaml
mosenergosbyt:
    # First account
  - username: !secret first_mosenergosbyt_username
    password: !secret first_mosenergosbyt_password
    # Second account
  - username: !secret second_mosenergosbyt_username
    password: !secret second_mosenergosbyt_password
    # Third account
  - username: !secret third_mosenergosbyt_username
    password: !secret third_mosenergosbyt_password 
```

### Update only specific accounts
**Option A:** Specify list of accounts
```yaml
mosenergosbyt:
  username: !secret mosenergosbyt_username
  password: !secret mosenergosbyt_password

  # list of account codes
  accounts: ['99999-999-99', '88888-888-88']
```
**Option B:** Additionally specify meters to show in HA
```yaml
mosenergosbyt:
  username: !secret mosenergosbyt_username
  password: !secret mosenergosbyt_password

  accounts:
    # account code -> meter ID
    99999-999-99: 123456789
    88888-888-88: ['321987654', '456789123']
```

### Change update schedule
Default `scan_interval`: 1 hour  
Default `login_timeout`: 1 hour
```yaml
mosenergosbyt:
  username: !secret mosenergosbyt_username
  password: !secret mosenergosbyt_password

  # Interval for entity updates
  scan_interval:
    hours: 6

  # Invalidate session after specified time period has passed
  # Session gets updated on the next entities update run 
  login_timeout:
    hours: 3
```