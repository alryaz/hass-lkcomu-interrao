# homeassistant-mosenergosbyt
The following custom component (whilst still in beta) provides with a certain degree of functionality at accessing Mosenergosbyt API. It will remain in active development until February, 2020.

Place the custom_components folder in your configuration directory (or add its contents to an existing custom_components folder).

Configuration is as follows:
```
sensor:
  - platform: mosenergosbyt
    username: !secret mosenergosbyt_username
    password: !secret mosenergosbyt_password
```

## HACS
Coming soon...