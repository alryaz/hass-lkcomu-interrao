# HomeAssistant Mosenergosbyt sensors
> Provide information about current state of your Mosenergosbyt accounts.
>
>[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
>[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
>[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/alryaz/hass-hekr-component/graphs/commit-activity)
>[![Donate Yandex](https://img.shields.io/badge/Donate-Yandex-red.svg)](https://money.yandex.ru/to/410012369233217)
>[![Donate PayPal](https://img.shields.io/badge/Donate-Paypal-blueviolet.svg)](https://www.paypal.me/alryaz)

This custom component provides Mosenergosbyt API polling capabilities to HomeAssistant.

## Screenshots
#### Account sensor
![Account sensor](https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/account.png)

#### Meter sensors
![MES+TKO Meter sensor](https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/meter_tko.png)
![MES Meter sensor](https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/meter.png)

#### Invoice sensor
![Invoice sensor](https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/account.png)


## Installation
### Via HACS
1. Open HACS (via `Extensions` in the sidebar)
1. Add a new custom repository:
   1. Select `Integration` as custom repository type
   1. Enter custom repository URL: `https://github.com/alryaz/hass-mosenergosbyt`
   1. Press `Add` button
   1. Wait until repository gets added 
   1. You should now see `Mosenergosbyt (Мосэнергосбыт)` integration available in the list of newly added integrations
1. Click `Install` button to view available versions
1. Install latest version by pressing `Install`

_NOTE:_ It is not recommended to install `master` branch. It is intended for development only. 

### Manually
Clone the repository to a temporary directory, then create a `custom_components` directory inside your HomeAssistant
config folder (if it doesn't exist yet). Then, move `mosenergosbyt` folder from `custom_components` folder of
the repository to the `custom_components` folder inside your HomeAssistant configuration.  
An example (assuming HomeAssistant configuration is available at `/mnt/homeassistant/config`) for Unix-based
systems is available below:
```
git clone https://github.com/alryaz/hass-mosenergosbyt.git hass-mosenergosbyt-sensor
mkdir -p /mnt/homeassistant/config/custom_components
mv hass-mosenergosbyt-sensor/custom_components/mosenergosbyt /mnt/homeassistant/config/custom_components
```

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

### Override default user agent
By default, `fake_useragent` ([link](https://pypi.org/project/fake-useragent/)) module attempts to generate a user
for the whole life span of user configuration. There is also a common failover user agent defined in code.
Should you be willing to set your own user agent, you are welcome to do it using configuration parameter
listed below:
```yaml
mosenergosbyt:
  ...
  # Custom user agent
  user_agent: 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.2 (KHTML, like Gecko) Chrome/22.0.1216.0 Safari/537.2'
  
  # Same user agent written using multiline string
  user_agent: >
    Mozilla/5.0 (Windows NT 6.1)
    AppleWebKit/537.2 (KHTML, like Gecko)
    Chrome/22.0.1216.0
    Safari/537.2
```