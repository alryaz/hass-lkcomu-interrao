# HomeAssistant Hekr Devices Integration
[![GitHub Page](https://img.shields.io/badge/GitHub-alryaz%2Fhass--mosenergosbyt-blue)](https://github.com/alryaz/hass-mosenergosbyt)
[![Donate Yandex](https://img.shields.io/badge/Donate-Yandex-red.svg)](https://money.yandex.ru/to/410012369233217)
[![Donate PayPal](https://img.shields.io/badge/Donate-Paypal-blueviolet.svg)](https://www.paypal.me/alryaz)
{% set mainline_num_ver = version_available.replace("v", "").replace(".", "") | int %}{%- set features = {
    'v0.2.2': 'Display TO VKGO service costs in invoices; pre-calculated submit dates for MES meters',
    'v0.2.0': 'Major architecture overhaul in preparation for new account types support (MES+TKO available already), invoices sensors, progress made towards integrating submissions',
    'v0.1.1': 'Name formatting for entities',
    'v0.1.0': 'Multiple accounts support, GUI configuration',
}-%}{%- set breaking_changes = {
    'v0.1.1': [['Account uses `account_code` attribute for its number instead of `number`']]
} -%}{%- set bugfixes = {
    'v0.2.2': ['Fixed non-negative value display for MES+TKO accounts'],
    'v0.2.1': ['Fixed reauthentication issue on network failure / server timeout']
} -%}
{% if installed %}{% if version_installed == "master" %}
#### ⚠ You are using development version
This branch may be unstable, as it contains commits not tested beforehand.  
Please, do not use this branch in production environments.
{% else %}{% if version_installed == version_available %}
#### ✔ You are using mainline version{% else %}{% set num_ver = version_installed.replace("v", "").replace(".","") | int %}
#### 🚨 You are using an outdated release of Hekr component{% if num_ver < 20 %}
{% set print_header = True %}{% for ver, changes in breaking_changes.items() %}{% set ver = ver.replace("v", "").replace(".","") | int %}{% if num_ver < ver %}{% if print_header %}
##### Breaking changes (`{{ version_installed }}` -> `{{ version_available }}`){% set print_header = False %}{% endif %}{% for change in changes %}
{{ '- '+change.pop(0) }}{% for changeline in change %}
{{ '  '+changeline }}{% endfor %}{% endfor %}{% endif %}{% endfor %}
{% endif %}{% endif %}

{% set print_header = True %}{% for ver, fixes in bugfixes.items() %}{% set ver = ver.replace("v", "").replace(".","") | int %}{% if num_ver < ver %}{% if print_header %}
##### Bug fixes (`{{ version_installed }}` -> `{{ version_available }}`){% set print_header = False %}{% endif %}{% for fix in fixes %}
{{ '- ' + fix }}{% endfor %}{% endif %}{% endfor %}

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

#### Meter sensors
![MES Meter sensor](https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/meter.png)
![MES+TKO Meter sensor](https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/meter_tko.png)

#### Invoice sensor
![Invoice sensor](https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/account.png)

## !!! WARNING !!!
Although indication submission is partially available in this version of the component, it is in no way
secure or error-proof. Since more testing is required, and there are date restrictions in place,
this feature will be complete by one of the next minor releases.

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
  ...
  # list of account codes
  accounts: ['99999-999-99', '88888-888-88']
```
**Option B:** Additionally specify meters to show in HA
```yaml
mosenergosbyt:
  ...
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
  ...
  # Interval for entity updates
  scan_interval:
    hours: 6

  # ... also possible to set via seconds
  scan_interval: 21600

  # Invalidate session after specified time period has passed
  # Session gets updated on the next entities update run 
  login_timeout:
    hours: 3
```

### Configure invoices
Invoice entities are updated during the main update schedule. They display the total amount
requested by the operating company. **They don't reflect whether your payment has already
been processed!** They are designed to serve as attribute holders for pricing decomposition.
```yaml
mosenergosbyt:
  ...
  # Enable invoices for every account (default behaviour)
  invoices: true

  # Enable invoices for certain accounts
  invoices: ['1131241222']

  # Disable invoices for every account
  invoices: false
```

### Custom names for entities
Currently, naming entities supports basic formatting based on python `str.format(...)` method. Changing
these parameters (assuming setup without explicit overrides via *Customize* interface or alike) will have effect both on entity IDs and friendly names.  
Supported replacements are: `code` (more will be added)
Default `account_name`: `MES Account {code}`  
Default `meter_name`: `MES Meter {code}`
Default: `invoice_name`: `MES Invoice {code}`
```yaml
mosenergosbyt:
  ...
  # Custom account name format
  account_name: 'My super {code} account' 

  # Custom meter name format
  meter_name: 'Meter {code} is electrifying'

  # Custom invoice name format
  meter_name: 'Invoice {code} is too much!'
```