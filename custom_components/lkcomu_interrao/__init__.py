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

import asyncio
import logging
from typing import Any, Mapping, TYPE_CHECKING
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
import voluptuous as vol

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import CONF_PASSWORD, CONF_TYPE, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from custom_components.lkcomu_interrao._base import UpdateDelegatorsDataType
from custom_components.lkcomu_interrao._schema import CONFIG_ENTRY_SCHEMA
from custom_components.lkcomu_interrao._util import (
    _find_existing_entry,
    _make_log_prefix,
    import_api_cls,
    mask_username,
)
from custom_components.lkcomu_interrao.const import *

if TYPE_CHECKING:
    from inter_rao_energosbyt.interfaces import Account, AccountID, BaseEnergosbytAPI

_LOGGER = logging.getLogger(__name__)


def _unique_entries(value: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    pairs: dict[tuple[str, str], int | None] = {}

    errors = []
    for i, config in enumerate(value):
        pair = (config[CONF_TYPE], config[CONF_USERNAME])
        if pair in pairs:
            if pairs[pair] is not None:
                errors.append(
                    vol.Invalid(
                        "duplicate unique key, first encounter", path=[pairs[pair]]
                    )
                )
                pairs[pair] = None
            errors.append(
                vol.Invalid("duplicate unique key, subsequent encounter", path=[i])
            )
        else:
            pairs[pair] = i

    if errors:
        if len(errors) > 1:
            raise vol.MultipleInvalid(errors)
        raise next(iter(errors))

    return value


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Any(
            vol.Equal({}),
            vol.All(
                cv.ensure_list,
                vol.Length(min=1),
                [CONFIG_ENTRY_SCHEMA],
                _unique_entries,
            ),
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up the Inter RAO component."""
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

        type_: str = user_cfg[CONF_TYPE]
        username: str = user_cfg[CONF_USERNAME]

        key = (type_, username)
        log_prefix = f"[{type_}/{mask_username(username)}] "

        _LOGGER.debug(log_prefix + "YAML configuration encountered")

        existing_entry = _find_existing_entry(hass, type_, username)
        if existing_entry:
            if existing_entry.source == SOURCE_IMPORT:
                yaml_config[key] = user_cfg
                _LOGGER.debug(log_prefix + "Matching config entry exists")
            else:
                _LOGGER.warning(
                    log_prefix + "YAML config is overridden by another entry!"
                )
            continue

        # Save YAML configuration
        yaml_config[key] = user_cfg

        _LOGGER.warning(log_prefix + "Creating new config entry")

        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data={
                    CONF_TYPE: type_,
                    CONF_USERNAME: username,
                },
            )
        )

    if not yaml_config:
        _LOGGER.debug("YAML configuration not found")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    type_ = entry.data[CONF_TYPE]
    username = entry.data[CONF_USERNAME]
    unique_key = (type_, username)
    entry_id = entry.entry_id
    log_prefix = f"[{type_}/{mask_username(username)}] "
    hass_data = hass.data

    # Source full configuration
    if entry.source == SOURCE_IMPORT:
        # Source configuration from YAML
        yaml_config = hass_data.get(DATA_YAML_CONFIG)

        if not yaml_config or unique_key not in yaml_config:
            _LOGGER.info(
                log_prefix
                + (f"Removing entry {entry_id} after removal from YAML configuration")
            )
            hass.async_create_task(hass.config_entries.async_remove(entry_id))
            return False

        user_cfg = yaml_config[unique_key]

    else:
        # Source and convert configuration from input post_fields
        all_cfg = {**entry.data}

        if entry.options:
            all_cfg.update(entry.options)

        try:
            user_cfg = CONFIG_ENTRY_SCHEMA(all_cfg)
        except vol.Invalid as e:
            _LOGGER.error(log_prefix + "Configuration invalid" + ": " + repr(e))
            return False

    _LOGGER.info(log_prefix + "Applying configuration entry")

    from inter_rao_energosbyt.exceptions import EnergosbytException

    try:
        api_cls = import_api_cls(type_)
    except (ImportError, AttributeError):
        _LOGGER.error(
            log_prefix
            + (
                "Could not find API type. This is a fatal error for the component. "
                "Please, report it to the developer (or open an issue on GitHub)."
            )
        )
        return False

    api_object = api_cls(
        username=username,
        password=user_cfg[CONF_PASSWORD],
        user_agent=user_cfg.get(CONF_USER_AGENT),
    )

    try:
        try:
            await api_object.async_authenticate()

            # Fetch all accounts
            accounts: Mapping[AccountID, "Account"] = (
                await api_object.async_update_accounts(with_related=True)
            )

        except EnergosbytException as e:
            err_cls = ConfigEntryNotReady
            err_txt = "Error during authentication"

            if len(e.args) == 3:
                error_code = e.args[1]
                if error_code in (131, 127, 114):
                    err_cls = ConfigEntryAuthFailed
                    err_txt = "Error authenticating"

            err_txt += ": " + repr(e)
            _LOGGER.error(log_prefix + err_txt)
            raise err_cls(repr(e))

    except BaseException:
        await api_object.async_close()
        raise

    if not accounts:
        # Cancel setup because no accounts provided
        _LOGGER.warning(log_prefix + ("No accounts found"))
        await api_object.async_close()
        return False

    _LOGGER.debug(log_prefix + (f"Found {len(accounts)} accounts"))

    profile_id = api_object.auth_session.id_profile

    api_objects: dict[str, "BaseEnergosbytAPI"] = hass_data.setdefault(
        DATA_API_OBJECTS, {}
    )
    for existing_config_entry_id, existing_api_object in api_objects.items():
        if existing_api_object.auth_session.id_profile == profile_id:
            _LOGGER.warning(
                log_prefix
                + (
                    f"Same profiles retrieved by multiple configurations "
                    f"(foreign username: {existing_api_object.username}, "
                    f"ID: {existing_config_entry_id})"
                )
            )
            await hass.config_entries.async_set_disabled_by(entry.entry_id, DOMAIN)
            return False

    # Create placeholders
    api_objects[entry_id] = api_object
    hass_data.setdefault(DATA_ENTITIES, {})[entry_id] = {}
    hass_data.setdefault(DATA_FINAL_CONFIG, {})[entry_id] = user_cfg
    hass.data.setdefault(DATA_UPDATE_DELEGATORS, {})[entry_id] = {}

    # Forward entry setup to sensor platform
    await hass.config_entries.async_forward_entry_setups(
        entry,
        [SENSOR_DOMAIN, BINARY_SENSOR_DOMAIN],
    )

    # Create options update listener
    update_listener = entry.add_update_listener(async_reload_entry)
    hass_data.setdefault(DATA_UPDATE_LISTENERS, {})[entry_id] = update_listener

    _LOGGER.debug(log_prefix + ("Setup successful"))
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Reload Lkcomu InterRAO entry"""
    log_prefix = _make_log_prefix(entry, "setup")
    _LOGGER.info(log_prefix + "Reloading configuration entry")
    return await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Lkcomu InterRAO entry"""
    log_prefix = _make_log_prefix(entry, "setup")
    entry_id = entry.entry_id

    update_delegators: UpdateDelegatorsDataType = hass.data[DATA_UPDATE_DELEGATORS].pop(
        entry_id
    )

    tasks = [
        hass.config_entries.async_forward_entry_unload(entry, domain)
        for domain in update_delegators.keys()
    ]

    unload_ok = all(await asyncio.gather(*tasks))

    if unload_ok:
        hass.data[DATA_API_OBJECTS].pop(entry_id)
        hass.data[DATA_FINAL_CONFIG].pop(entry_id)

        cancel_listener = hass.data[DATA_UPDATE_LISTENERS].pop(entry_id)
        cancel_listener()

        _LOGGER.info(log_prefix + "Unloaded configuration entry")

    else:
        _LOGGER.warning(log_prefix + "Failed to unload configuration entry")

    return unload_ok
