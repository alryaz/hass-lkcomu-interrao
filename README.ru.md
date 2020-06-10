# HomeAssistant сенсоры Мосэнергосбыт
> Предоставление информации о текущем состоянии ваших аккаунтов в Мосэнергосбыт.
>
>[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
>[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
>[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/alryaz/hass-hekr-component/graphs/commit-activity)
>[![Пожертвование Yandex](https://img.shields.io/badge/%D0%9F%D0%BE%D0%B6%D0%B5%D1%80%D1%82%D0%B2%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5-Yandex-red.svg)](https://money.yandex.ru/to/410012369233217)
>[![Пожертвование PayPal](https://img.shields.io/badge/%D0%9F%D0%BE%D0%B6%D0%B5%D1%80%D1%82%D0%B2%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5-Paypal-blueviolet.svg)](https://www.paypal.me/alryaz)

Данная интеграция предоставляет возможность системе HomeAssistant опрашивать API Мосэнергосбыта.

## Установка
### Посредством HACS
1. Откройте HACS (через `Extensions` в боковой панели)
1. Добавьте новый произвольный репозиторий:
   1. Выберите `Integration` (`Интеграция`) в качестве типа репозитория
   1. Введите ссылку на репозиторий: `https://github.com/alryaz/hass-mosenergosbyt`
   1. Нажмите кнопку `Add` (`Добавить`)
   1. Дождитесь добавления репозитория
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

### Custom names for entities
Currently, naming entities supports basic formatting based on python `str.format(...)` method. Changing
these parameters (assuming setup without explicit overrides via *Customize* interface or alike) will have effect both on entity IDs and friendly names.  
Supported replacements are: `code` (more will be added)
Default `account_name`: `MES Account {code}`  
Default `meter_name`: `MES Meter {code}`
```yaml
mosenergosbyt:
  username: !secret mosenergosbyt_username
  password: !secret mosenergosbyt_password

  # Custom account name format
  account_name: 'My super {code} account' 
  # Custom meter name format
  meter_name: 'Meter {code} is electrifying'
```