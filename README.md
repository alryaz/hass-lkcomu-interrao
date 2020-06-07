# Home Assistant Mosenergosbyt sensors
> Provide information about current state of your Mosenergosbyt account.
>
>[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
>[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
>[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/alryaz/hass-hekr-component/graphs/commit-activity)
>[![Donate Yandex](https://img.shields.io/badge/Donate-Yandex-red.svg)](https://money.yandex.ru/to/410012369233217)
>[![Donate PayPal](https://img.shields.io/badge/Donate-Paypal-blueviolet.svg)](https://www.paypal.me/alryaz)

This custom component provides Mosenergosbyt API polling capabilities to HomeAssistant.

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
git clone https://github.com/alryaz/hass-mosenergosbyt-sensor.git hass-mosenergosbyt-sensor
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