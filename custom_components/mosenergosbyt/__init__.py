"""Mosenergosbyt API"""
import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Optional, List

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD,
                                 CONF_SCAN_INTERVAL, CONF_ENTITY_ID, EVENT_HOMEASSISTANT_STOP)
from homeassistant.core import callback
from homeassistant.helpers.typing import HomeAssistantType, ConfigType

if TYPE_CHECKING:
    from .mosenergosbyt import API
    from .sensor import MESAccountSensor

_LOGGER = logging.getLogger(__name__)

CONF_ACCOUNTS = "accounts"
CONF_METERS = "meters"
CONF_LOGIN_TIMEOUT = "login_timeout"
CONF_METER_NAME = "meter_name"
CONF_ACCOUNT_NAME = "account_name"

ATTR_INDICATIONS = "indications"

DOMAIN = 'mosenergosbyt'
DATA_CONFIG = DOMAIN + '_config'
DATA_API_OBJECTS = DOMAIN + '_api_objects'
DATA_ENTITIES = DOMAIN + '_created_entities'
DATA_UPDATERS = DOMAIN + '_updaters'

DEFAULT_SCAN_INTERVAL = timedelta(hours=1)
DEFAULT_LOGIN_TIMEOUT = timedelta(seconds=60 * 60)
DEFAULT_METER_NAME_FORMAT = 'MES Meter {code}'
DEFAULT_ACCOUNT_NAME_FORMAT = 'MES Account {code}'

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(cv.ensure_list, [vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_ACCOUNTS, default=[]): vol.Any(
                    vol.All(cv.ensure_list, [cv.string]),
                    {cv.string: vol.Any(
                        vol.All(cv.ensure_list, [cv.string]),
                        vol.All(cv.boolean, True)
                    )}
                ),
                vol.Optional(CONF_METER_NAME, default=DEFAULT_METER_NAME_FORMAT): cv.string,
                vol.Optional(CONF_ACCOUNT_NAME, default=DEFAULT_ACCOUNT_NAME_FORMAT): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL):
                    vol.All(cv.time_period, cv.positive_timedelta),
                vol.Optional(CONF_LOGIN_TIMEOUT, default=DEFAULT_LOGIN_TIMEOUT):
                    vol.All(cv.time_period, cv.positive_timedelta),
            }
        )])
    },
    extra=vol.ALLOW_EXTRA,
)

INDICATIONS_SCHEMA = vol.Schema({str: int})

SERVICE_PUSH_INDICATIONS = 'push_indications'
SERVICE_PUSH_INDICATIONS_PAYLOAD_SCHEMA = vol.Schema({
    vol.Required(CONF_ENTITY_ID): cv.entity_id,
    vol.Required(ATTR_INDICATIONS): INDICATIONS_SCHEMA
})

SERVICE_CALCULATE_INDICATIONS = 'push_indications'
SERVICE_CALCULATE_INDICATIONS_PAYLOAD_SCHEMA = vol.Schema({
    vol.Required(CONF_ENTITY_ID): cv.entity_id,
    vol.Required(ATTR_INDICATIONS): INDICATIONS_SCHEMA
})


@callback
def _find_existing_entry(hass: HomeAssistantType, username: str) -> Optional[config_entries.ConfigEntry]:
    existing_entries = hass.config_entries.async_entries(DOMAIN)
    for config_entry in existing_entries:
        if config_entry.data[CONF_USERNAME] == username:
            return config_entry


async def async_setup(hass: HomeAssistantType, config: ConfigType):
    """Set up the Mosenergosbyt component."""
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _close_api_sessions)

    def _push_indications(call):
        # @TODO: stub
        return True

    hass.services.async_register(
        DOMAIN, SERVICE_PUSH_INDICATIONS,
        _push_indications, SERVICE_PUSH_INDICATIONS_PAYLOAD_SCHEMA)

    def _calculate_indications(call):
        # @TODO: stub
        return True

    hass.services.async_register(
        DOMAIN, SERVICE_PUSH_INDICATIONS,
        _calculate_indications, SERVICE_CALCULATE_INDICATIONS_PAYLOAD_SCHEMA)

    domain_config = config.get(DOMAIN)
    if not domain_config:
        return True

    domain_data = {}
    hass.data[DOMAIN] = domain_data

    yaml_config = {}
    hass.data[DATA_CONFIG] = yaml_config

    for user_cfg in domain_config:

        username = user_cfg[CONF_USERNAME]

        _LOGGER.debug('User "%s" entry from YAML' % username)

        existing_entry = _find_existing_entry(hass, username)
        if existing_entry:
            if existing_entry.source == config_entries.SOURCE_IMPORT:
                yaml_config[username] = user_cfg
                _LOGGER.debug('Skipping existing import binding')
            else:
                _LOGGER.warning('YAML config for user %s is overridden by another config entry!' % username)
            continue

        if username in yaml_config:
            _LOGGER.warning('User "%s" set up multiple times. Check your configuration.' % username)
            continue

        yaml_config[username] = user_cfg
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data={CONF_USERNAME: username},
            )
        )

    return True


async def _close_api_sessions(hass: HomeAssistantType, entry_id: Optional[str] = None, *_):
    if DATA_ENTITIES in hass.data:
        if entry_id:
            entities: Optional[List['MESAccountSensor']] = hass.data[DATA_ENTITIES].get(entry_id)

        else:
            entities: List['MESAccountSensor'] = []
            for entry_entities in hass.data[DATA_ENTITIES]:
                entities.extend(entry_entities)

        if entities:
            tasks = [
                hass.async_create_task(entity.account.api.logout())
                for entity in entities
                if entity.account
            ]
            await asyncio.wait(tasks)


async def async_setup_entry(hass: HomeAssistantType, config_entry: config_entries.ConfigEntry):
    user_cfg = config_entry.data
    username = user_cfg[CONF_USERNAME]

    if config_entry.source == config_entries.SOURCE_IMPORT:
        yaml_config = hass.data.get(DATA_CONFIG)
        if not yaml_config or username not in yaml_config:
            _LOGGER.info('Removing entry %s after removal from YAML configuration.' % config_entry.entry_id)
            hass.async_create_task(
                hass.config_entries.async_remove(config_entry.entry_id)
            )
            return False

        user_cfg = yaml_config.get(username)

    _LOGGER.debug('Setting up config entry for user "%s"' % username)

    from .mosenergosbyt import API, MosenergosbytException

    try:
        api_object = API(username, user_cfg[CONF_PASSWORD])

        await api_object.login()

        accounts = await api_object.get_accounts()

        if CONF_ACCOUNTS in user_cfg and user_cfg[CONF_ACCOUNTS]:
            accounts = {k: v for k, v in accounts.items() if k in user_cfg[CONF_ACCOUNTS]}

    except MosenergosbytException as e:
        _LOGGER.error('Error authenticating with user "%s": %s' % (username, str(e)))
        return False

    if not accounts:
        _LOGGER.warning('No accounts found under username "%s"' % username)
        return False

    hass.data.setdefault(DATA_API_OBJECTS, {})[config_entry.entry_id] = api_object

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(
            config_entry,
            SENSOR_DOMAIN
        )
    )

    _LOGGER.debug('Successfully set up user "%s"' % username)
    return True


async def async_unload_entry(hass: HomeAssistantType, config_entry: config_entries.ConfigEntry):
    entry_id = config_entry.entry_id

    if DATA_UPDATERS in hass.data and entry_id in hass.data[DATA_UPDATERS]:
        # Remove API objects
        hass.data[DATA_UPDATERS].pop(entry_id)
        if not hass.data[DATA_UPDATERS]:
            del hass.data[DATA_UPDATERS]

    if DATA_API_OBJECTS in hass.data and entry_id in hass.data[DATA_API_OBJECTS]:
        # Remove API objects
        del hass.data[DATA_API_OBJECTS][entry_id]
        if not hass.data[DATA_API_OBJECTS]:
            del hass.data[DATA_API_OBJECTS]

    if DATA_ENTITIES in hass.data and entry_id in hass.data[DATA_ENTITIES]:
        # Remove references to created entities
        await _close_api_sessions(hass)

        del hass.data[DATA_ENTITIES][entry_id]
        hass.async_create_task(
            hass.config_entries.async_forward_entry_unload(
                config_entry,
                SENSOR_DOMAIN
            )
        )
        if not hass.data[DATA_ENTITIES]:
            del hass.data[DATA_ENTITIES]
