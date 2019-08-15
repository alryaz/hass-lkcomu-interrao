"""Mosenergosbyt API"""
import logging
from datetime import timedelta

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD,
                                 CONF_SCAN_INTERVAL, CONF_ENTITY_ID,
                                 ATTR_ENTITY_ID)
from homeassistant.helpers.discovery import async_load_platform
from .mosenergosbyt import MESAPI

_LOGGER = logging.getLogger(__name__)

CONF_ACCOUNTS = "accounts"

ATTR_INDICATIONS = "indications"

DOMAIN = 'mosenergosbyt'

DEFAULT_INTERVAL = timedelta(hours=1)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_ACCOUNTS, default=[]): cv.ensure_list,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_INTERVAL): cv.time_period,
            }
        )
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


async def async_setup(hass, config):

    """Set up the Speedtest.net component."""
    conf = config[DOMAIN]
    api_object = MESAPI(conf[CONF_USERNAME], conf[CONF_PASSWORD])

    _LOGGER.debug('Creating mosenergosbyt sensors')

    hass.async_create_task(
        async_load_platform(
            hass, SENSOR_DOMAIN, DOMAIN,
            api_object.GetAccountsList(conf[CONF_ACCOUNTS]), config
        )
    )

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

    return True
