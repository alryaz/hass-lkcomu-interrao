"""Energosbyt API"""
__all__ = (
    "CONFIG_SCHEMA",
    "async_unload_entry",
    "async_reload_entry",
    "async_setup",
    "async_setup_entry",
    "config_flow",
    "const",
    "sensor",
    "DOMAIN",
)

import logging
from typing import Mapping, TYPE_CHECKING

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import CONF_PASSWORD, CONF_TYPE, CONF_USERNAME
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from custom_components.lkcomu_interrao._schema import CONFIG_ENTRY_SCHEMA

from custom_components.lkcomu_interrao._util import (
    _find_existing_entry,
    _make_log_prefix,
    import_api_cls,
)
from custom_components.lkcomu_interrao.const import (
    API_TYPE_DEFAULT,
    API_TYPE_NAMES,
    CONF_ACCOUNTS,
    CONF_FILTER,
    CONF_INVOICES,
    CONF_METERS,
    CONF_NAME_FORMAT,
    CONF_USER_AGENT,
    DATA_API_OBJECTS,
    DATA_ENTITIES,
    DATA_FINAL_CONFIG,
    DATA_UPDATERS,
    DATA_UPDATE_LISTENERS,
    DATA_YAML_CONFIG,
    DEFAULT_NAME_FORMAT_ACCOUNTS,
    DEFAULT_NAME_FORMAT_INVOICES,
    DEFAULT_NAME_FORMAT_METERS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

if TYPE_CHECKING:
    from inter_rao_energosbyt.interfaces import Account
    from custom_components.lkcomu_interrao.sensor import MESAccountSensor

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Any(
            vol.Equal({}),
            vol.All(cv.ensure_list, [CONFIG_ENTRY_SCHEMA], vol.Length(min=1)),
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistantType, config: ConfigType):
    """Set up the Mosenergosbyt component."""
    domain_config = config.get(DOMAIN)
    if not domain_config:
        return True

    domain_data = {}
    hass.data[DOMAIN] = domain_data

    yaml_config = {}
    hass.data[DATA_YAML_CONFIG] = yaml_config

    for user_cfg in domain_config:
        if not user_cfg:
            continue

        type_ = user_cfg[CONF_TYPE]
        username = user_cfg[CONF_USERNAME]

        key = (type_, username)

        _LOGGER.debug('User "%s" entry from YAML' % username)

        existing_entry = _find_existing_entry(hass, type_, username)
        if existing_entry:
            if existing_entry.source == config_entries.SOURCE_IMPORT:
                yaml_config[key] = user_cfg
                _LOGGER.debug("Skipping existing import binding")
            else:
                _LOGGER.warning(
                    "YAML config for user %s is overridden by another config entry!" % username
                )
            continue

        if key in yaml_config:
            _LOGGER.warning('User "%s" set up multiple times. Check your configuration.' % username)
            continue

        yaml_config[key] = user_cfg

        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data={
                    CONF_TYPE: type_,
                    CONF_USERNAME: username,
                },
            )
        )

    if yaml_config:
        _LOGGER.debug(
            "YAML usernames: %s",
            '"' + '", "'.join(map(lambda x: "->".join(x), yaml_config.keys())) + '"',
        )
    else:
        _LOGGER.debug("No configuration added from YAML")

    return True


async def async_setup_entry(hass: HomeAssistantType, config_entry: config_entries.ConfigEntry):
    type_ = config_entry.data[CONF_TYPE]
    username = config_entry.data[CONF_USERNAME]
    key = (type_, username)

    # Check if leftovers from previous setup are present
    if config_entry.entry_id in hass.data.get(DATA_FINAL_CONFIG, {}):
        raise ConfigEntryNotReady(
            'Configuration entry with type "%s" and username "%s" already set up' % key
        )

    # Source full configuration
    if config_entry.source == config_entries.SOURCE_IMPORT:
        # Source configuration from YAML
        yaml_config = hass.data.get(DATA_YAML_CONFIG)

        if not yaml_config or key not in yaml_config:
            _LOGGER.info(
                "Removing entry %s after removal from YAML configuration." % config_entry.entry_id
            )
            hass.async_create_task(hass.config_entries.async_remove(config_entry.entry_id))
            return False

        user_cfg = yaml_config[key]

    else:
        # Source and convert configuration from input post_fields
        all_cfg = {**config_entry.data}

        if config_entry.options:
            all_cfg.update(config_entry.options)

        user_cfg = CONFIG_ENTRY_SCHEMA(all_cfg)

    _LOGGER.info('Setting up config entry for user "%s"' % username)

    from inter_rao_energosbyt.exceptions import EnergosbytException

    type_ = user_cfg[CONF_TYPE]

    try:
        api_cls = import_api_cls(type_)
    except (ImportError, AttributeError):
        _LOGGER.error("Could not find API type: %s", type_)
        return False

    try:
        api_object = api_cls(
            username=username,
            password=user_cfg[CONF_PASSWORD],
            user_agent=user_cfg.get(CONF_USER_AGENT),
        )

        await api_object.async_authenticate()

        # Fetch all accounts
        accounts: Mapping[int, "Account"] = await api_object.async_update_accounts(
            with_related=True
        )

    except EnergosbytException as e:
        _LOGGER.error('Error authenticating with user "%s": %s' % (username, str(e)))
        return False

    if not accounts:
        # Cancel setup because no accounts provided
        _LOGGER.warning('No supported accounts found under username "%s"', username)
        return False

    # Create post_fields placeholders
    hass.data.setdefault(DATA_API_OBJECTS, {})[key] = api_object
    hass.data.setdefault(DATA_ENTITIES, {})[key] = {}
    hass.data.setdefault(DATA_UPDATERS, {})[key] = {}

    # Save final configuration post_fields
    hass.data.setdefault(DATA_FINAL_CONFIG, {})[key] = user_cfg

    # Forward entry setup to sensor platform
    for domain in (SENSOR_DOMAIN, BINARY_SENSOR_DOMAIN):
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(
                config_entry,
                domain,
            )
        )

    hass.data.setdefault(DATA_UPDATE_LISTENERS, {})[key] = config_entry.add_update_listener(
        async_reload_entry
    )

    _LOGGER.debug('Successfully set up type "%s" and username "%s"' % key)
    return True


async def async_reload_entry(
    hass: HomeAssistantType, config_entry: config_entries.ConfigEntry
) -> None:
    """Reload Mosenergosbyt entry"""
    _LOGGER.info(_make_log_prefix(config_entry, "setup") + "Reloading configuration entry")
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistantType, config_entry: config_entries.ConfigEntry
) -> bool:
    """Unload Mosenergosbyt entry"""
    log_prefix = _make_log_prefix(config_entry, "setup")
    entry_id = config_entry.entry_id

    unload_ok = await hass.config_entries.async_forward_entry_unload(config_entry, SENSOR_DOMAIN)

    if unload_ok:
        hass.data[DATA_API_OBJECTS].pop(entry_id)
        hass.data[DATA_FINAL_CONFIG].pop(entry_id)
        cancel_listener = hass.data[DATA_UPDATE_LISTENERS].pop(entry_id)
        cancel_listener()

        _LOGGER.info(log_prefix + "Unloaded configuration entry")

    else:
        _LOGGER.warning(log_prefix + "Failed to unload configuration entry")

    return unload_ok
