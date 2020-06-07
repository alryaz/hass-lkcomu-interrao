"""
Sensor for Mosenergosbyt cabinet.
Retrieves values regarding current state of accounts.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from functools import partial
from typing import TYPE_CHECKING, Dict, Optional

from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_SCAN_INTERVAL
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import HomeAssistantType, ConfigType

from . import DATA_CONFIG, CONF_ACCOUNTS, DEFAULT_SCAN_INTERVAL, DATA_API_OBJECTS, DATA_ENTITIES, DATA_UPDATERS, \
    CONF_LOGIN_TIMEOUT, DEFAULT_LOGIN_TIMEOUT, DEFAULT_METER_NAME_FORMAT, CONF_METER_NAME, CONF_ACCOUNT_NAME, \
    DEFAULT_ACCOUNT_NAME_FORMAT

from .mosenergosbyt import MosenergosbytException

if TYPE_CHECKING:
    from .mosenergosbyt import API, Account, Meter

_LOGGER = logging.getLogger(__name__)

ENTITIES_ACCOUNT = 'account'
ENTITIES_METER_TARIFF = 'meter_tariff'


async def _entity_updater(hass: HomeAssistantType, entry_id: str, user_cfg: ConfigType, async_add_entities,
                          now: Optional[datetime] = None):
    _LOGGER.debug('Running updater for entry %s at %s' % (entry_id, now or datetime.now()))
    api: 'API' = hass.data.get(DATA_API_OBJECTS, {}).get(entry_id)
    if not api:
        _LOGGER.debug('Updater for entry %s found no API object' % entry_id)
        return False

    if api.logged_in_at + user_cfg[CONF_LOGIN_TIMEOUT] <= datetime.utcnow():
        _LOGGER.debug('Refreshing authentication for %s' % entry_id)
        await api.logout()
        await api.login()

    username = user_cfg[CONF_USERNAME]
    use_meter_filter = CONF_ACCOUNTS in user_cfg and user_cfg[CONF_ACCOUNTS]

    meter_name_format = user_cfg.get(CONF_METER_NAME, DEFAULT_METER_NAME_FORMAT)
    account_name_format = user_cfg.get(CONF_ACCOUNT_NAME, DEFAULT_ACCOUNT_NAME_FORMAT)

    accounts = await api.get_accounts()

    created_entities = hass.data.setdefault(DATA_ENTITIES, {}).get(entry_id)
    if created_entities is None:
        created_entities = {}
        hass.data[DATA_ENTITIES][entry_id] = created_entities

    new_accounts = {}
    new_meters = {}

    tasks = []
    for account_code, account in accounts.items():
        _LOGGER.debug('Setting up account %s for username %s' % (account_code, username))

        account_entity = created_entities.get(account_code)
        if account_entity is None:
            account_entity = MESAccountSensor(account, account_name_format)
            new_accounts[account_code] = account_entity
            tasks.append(account_entity.async_update())
        else:
            account_entity.account = account
            account_entity.async_schedule_update_ha_state(force_refresh=True)

        meters = await account.get_meters()

        if use_meter_filter:
            account_filter = user_cfg[CONF_ACCOUNTS][account_code]

            if account_filter is not True:
                meters = {k: v for k, v in meters if k in account_filter}

        if account_entity.meter_entities is None:
            meter_entities = {}
            account_entity.meter_entities = meter_entities

        else:
            meter_entities = account_entity.meter_entities

            for meter_id in meter_entities.keys() - meters.keys():
                tasks.append(hass.async_create_task(meter_entities[meter_id].async_remove()))
                del meter_entities[meter_id]

        for meter_id, meter in meters.items():
            meter_entity = meter_entities.get(meter_id)

            if meter_entity is None:
                meter_entity = MESMeterSensor(meter, meter_name_format)
                meter_entities[meter_id] = meter_entity
                new_meters[meter_id] = meter_entity
                tasks.append(meter_entity.async_update())
            else:
                meter_entity.meter = meter
                meter_entity.async_schedule_update_ha_state(force_refresh=True)

    if tasks:
        await asyncio.wait(tasks)

    if new_accounts:
        async_add_entities(new_accounts.values())

    if new_meters:
        async_add_entities(new_meters.values())

    created_entities.update(new_accounts)

    _LOGGER.debug('Successful update on entry %s' % entry_id)
    _LOGGER.debug('New meters: %s' % new_meters)
    _LOGGER.debug('New accounts: %s' % new_accounts)

    return len(new_accounts), len(new_meters)


async def async_setup_entry(hass: HomeAssistantType, config_entry: config_entries.ConfigEntry, async_add_devices):
    user_cfg = {**config_entry.data}
    username = user_cfg[CONF_USERNAME]

    _LOGGER.debug('Setting up entry for username "%s" from sensors' % username)

    if config_entry.source == config_entries.SOURCE_IMPORT:
        user_cfg = hass.data[DATA_CONFIG].get(username)
        scan_interval = user_cfg[CONF_SCAN_INTERVAL]

    elif CONF_SCAN_INTERVAL in user_cfg:
        scan_interval = timedelta(seconds=user_cfg[CONF_SCAN_INTERVAL])
        user_cfg[CONF_LOGIN_TIMEOUT] = timedelta(seconds=user_cfg[CONF_LOGIN_TIMEOUT])

    else:
        scan_interval = DEFAULT_SCAN_INTERVAL
        user_cfg[CONF_LOGIN_TIMEOUT] = DEFAULT_LOGIN_TIMEOUT

    update_call = partial(_entity_updater, hass, config_entry.entry_id, user_cfg, async_add_devices)

    try:
        result = await update_call()

        if result is False:
            return False

        if not sum(result):
            _LOGGER.warning('No accounts or meters discovered, check your configuration')
            return True

        hass.data.setdefault(DATA_UPDATERS, {})[config_entry.entry_id] = \
            async_track_time_interval(hass, update_call, scan_interval)

        new_accounts, new_meters = result

        _LOGGER.info('Set up %d accounts and %d meters, will refresh every %s seconds'
                     % (new_accounts, new_meters, scan_interval.seconds + scan_interval.days*86400))
        return True

    except MosenergosbytException as e:
        raise PlatformNotReady('Error while setting up entry "%s": %s' % (config_entry.entry_id, str(e))) from None


async def async_setup_platform(hass: HomeAssistantType, config: ConfigType, async_add_entities,
                               discovery_info=None):
    """Set up the sensor platform"""
    return False


class MESEntity(Entity):
    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.

        False if entity pushes its state to HA.
        """
        return False


class MESAccountSensor(MESEntity):
    """The class for this sensor"""
    def __init__(self, account: 'Account', name_format: str):
        self._state = None
        self._unit = None
        self._attributes = None

        self._name_format = name_format

        self.account = account

        self.meter_entities: Optional[Dict[str, 'MESMeterSensor']] = None

    async def async_update(self):
        """The update method"""
        try:
            _LOGGER.debug('Updating account %s' % self)
            last_payment = await self.account.get_last_payment()
            current_balance = await self.account.get_current_balance()
            remaining_days = await self.account.get_remaining_days()
        except MosenergosbytException as e:
            _LOGGER.debug('Retrieving data from Mosenergosbyt failed: %s' % e)
            return False

        attributes = {
            'account_code': self.account.account_code,
            'balance': current_balance,
            'address': self.account.address,
            'last_payment_date': last_payment['date'],
            'last_payment_amount': last_payment['amount'],
            'last_payment_status': last_payment['status'],
            'remaining_days': remaining_days,
        }

        self._unit = 'руб.'
        self._attributes = attributes
        self._state = (
            '+' if current_balance > 0
            else '-' if current_balance < 0
            else ''
        ) + str(current_balance)
        _LOGGER.debug('Update for account %s finished' % self)

    @property
    def name(self):
        """Return the name of the sensor"""
        return self._name_format.format(code=self.account.account_code)

    @property
    def state(self):
        """Return the state of the sensor"""
        return self._state

    @property
    def icon(self):
        """Return the icon of the sensor"""
        return 'mdi:flash-circle'

    # # @TODO: find a better way to integrate pictures (1/2)
    #    @property
    #    def entity_picture(self):
    #        return DEFAULT_PICTURE_ICON

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def device_state_attributes(self):
        """Return the attribute(s) of the sensor"""
        return self._attributes

    @property
    def unique_id(self):
        """Return the unique ID of the sensor"""
        return 'ls_' + str(self.account.service_id)


class MESMeterSensor(MESEntity):
    """The class for this sensor"""
    def __init__(self, meter: 'Meter', name_format: str):
        self._entity_picture = None
        self._state = None
        self._attributes = None

        self._name_format = name_format

        self.meter = meter

    async def async_update(self):
        """The update method"""
        attributes = {
            'account_code': self.meter.account_code,
            'install_date': self.meter.install_date,
            'remaining_days': self.meter.remaining_days,
        }
        for tariff, value in self.meter.submitted_indications.items():
            attributes['submitted_value_' + tariff.lower()] = value
        for tariff, value in self.meter.last_indications.items():
            attributes['last_value_' + tariff.lower()] = value

        self._state = self.meter.current_status
        self._attributes = attributes

    @property
    def name(self):
        """Return the name of the sensor"""
        return self._name_format.format(code=self.meter.meter_id)

    @property
    def state(self):
        """Return the state of the sensor"""
        return self._state

    @property
    def icon(self):
        """Return the icon of the sensor"""
        return 'mdi:counter'

    # # @TODO: find a better way to integrate pictures (2/2)
    #    @property
    #    def entity_picture(self):
    #        return DEFAULT_PICTURE_ICON

    @property
    def device_state_attributes(self):
        """Return the attribute(s) of the sensor"""
        return self._attributes

    @property
    def unique_id(self):
        """Return the unique ID of the sensor"""
        return 'meter_' + str(self.meter.meter_id)
