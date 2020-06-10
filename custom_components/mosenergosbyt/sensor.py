"""
Sensor for Mosenergosbyt cabinet.
Retrieves values regarding current state of accounts.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from functools import partial
from typing import TYPE_CHECKING, Dict, Optional, Tuple, Union

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_SCAN_INTERVAL, ATTR_ENTITY_ID, CONF_ENTITY_ID, STATE_OK, \
    STATE_LOCKED, STATE_UNKNOWN
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import HomeAssistantType, ConfigType, ServiceCallType

from . import DATA_CONFIG, CONF_ACCOUNTS, DEFAULT_SCAN_INTERVAL, DATA_API_OBJECTS, DATA_ENTITIES, DATA_UPDATERS, \
    CONF_LOGIN_TIMEOUT, DEFAULT_LOGIN_TIMEOUT, DEFAULT_METER_NAME_FORMAT, CONF_METER_NAME, CONF_ACCOUNT_NAME, \
    DEFAULT_ACCOUNT_NAME_FORMAT, DOMAIN, CONF_INVOICES, DEFAULT_INVOICE_NAME_FORMAT, CONF_INVOICE_NAME
from .mosenergosbyt import MosenergosbytException, ServiceType, MESElectricityMeter, _BaseMeter, \
    _BaseAccount, Invoice

if TYPE_CHECKING:
    from .mosenergosbyt import API

_LOGGER = logging.getLogger(__name__)

ENTITIES_ACCOUNT = 'account'
ENTITIES_METER_TARIFF = 'meter_tariff'

ATTR_INDICATIONS = "indications"
ATTR_IGNORE_PERIOD = "ignore_period"

DEFAULT_MAX_INDICATIONS = 3
INDICATIONS_SCHEMA = vol.Any(
    {vol.All(int, vol.Range(1, DEFAULT_MAX_INDICATIONS)): cv.positive_int},
    vol.All([cv.positive_int], vol.Length(1, DEFAULT_MAX_INDICATIONS))
)

SERVICE_PUSH_INDICATIONS = 'push_indications'
SERVICE_PUSH_INDICATIONS_PAYLOAD_SCHEMA = vol.Schema({
    vol.Required(CONF_ENTITY_ID): cv.entity_id,
    vol.Required(ATTR_INDICATIONS): INDICATIONS_SCHEMA,
    vol.Optional(ATTR_IGNORE_PERIOD, default=False): cv.boolean,
})

SERVICE_CALCULATE_INDICATIONS = 'calculate_indications'
SERVICE_CALCULATE_INDICATIONS_PAYLOAD_SCHEMA = vol.Schema({
    vol.Required(CONF_ENTITY_ID): cv.entity_id,
    vol.Required(ATTR_INDICATIONS): INDICATIONS_SCHEMA,
    vol.Optional(ATTR_IGNORE_PERIOD, default=False): cv.boolean,
})


async def _entity_updater(hass: HomeAssistantType, entry_id: str, user_cfg: ConfigType, async_add_entities,
                          now: Optional[datetime] = None) -> Union[bool, Tuple[int, int, int]]:
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
    use_invoice_filter = CONF_INVOICES in user_cfg and user_cfg[CONF_INVOICES]

    # Fetch custom name formats (or select defaults)
    meter_name_format = user_cfg.get(CONF_METER_NAME, DEFAULT_METER_NAME_FORMAT)
    account_name_format = user_cfg.get(CONF_ACCOUNT_NAME, DEFAULT_ACCOUNT_NAME_FORMAT)
    invoice_name_format = user_cfg.get(CONF_INVOICE_NAME, DEFAULT_INVOICE_NAME_FORMAT)

    # Account fetching phase
    accounts = await api.get_accounts()

    created_entities = hass.data.setdefault(DATA_ENTITIES, {}).get(entry_id)
    if created_entities is None:
        created_entities = {}
        hass.data[DATA_ENTITIES][entry_id] = created_entities

    new_accounts = {}
    new_meters = {}
    new_invoices = {}

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

        # Process meters
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

            for meter_code in meter_entities.keys() - meters.keys():
                tasks.append(hass.async_create_task(meter_entities[meter_code].async_remove()))
                del meter_entities[meter_code]

        for meter_code, meter in meters.items():
            meter_entity = meter_entities.get(meter_code)

            if meter_entity is None:
                meter_entity = MESMeterSensor(meter, meter_name_format)
                meter_entities[meter_code] = meter_entity
                new_meters[meter_code] = meter_entity
                tasks.append(meter_entity.async_update())

            else:
                meter_entity.meter = meter
                meter_entity.async_schedule_update_ha_state(force_refresh=True)

        # Check invoice filter
        if use_invoice_filter:
            invoice_filter = user_cfg[CONF_INVOICES]

            if invoice_filter is False:
                continue

            if invoice_filter is not True and account_code not in invoice_filter:
                continue

        # Process last invoice
        invoice = await account.get_last_invoice()

        if invoice:
            if account_entity.invoice_entity is None:
                invoice_entity = MESInvoiceSensor(invoice, invoice_name_format)
                account_entity.invoice_entity = invoice_entity
                new_invoices[invoice.invoice_id] = invoice_entity
                tasks.append(invoice_entity.async_update())

            else:
                if account_entity.invoice_entity.invoice.invoice_id != invoice.invoice_id:
                    account_entity.invoice_entity.invoice = invoice
                    account_entity.async_schedule_update_ha_state(force_refresh=True)

    if tasks:
        await asyncio.wait(tasks)

    if new_accounts:
        async_add_entities(new_accounts.values())

    if new_meters:
        async_add_entities(new_meters.values())

    if new_invoices:
        async_add_entities(new_invoices.values())

    created_entities.update(new_accounts)

    _LOGGER.debug('Successful update on entry %s' % entry_id)
    _LOGGER.debug('New meters: %s' % new_meters)
    _LOGGER.debug('New accounts: %s' % new_accounts)

    return len(new_accounts), len(new_meters), len(new_invoices)


async def async_register_services(hass: HomeAssistantType):
    if hass.services.has_service(DOMAIN, SERVICE_PUSH_INDICATIONS):
        return

    async def async_push_indications(call: ServiceCallType):
        entity_id = call.data[ATTR_ENTITY_ID]
        entry_accounts: Dict[str, Dict[str, 'MESAccountSensor']] = hass.data.get(DATA_ENTITIES, {})

        for account_sensors in entry_accounts.values():
            for account_sensor in account_sensors.values():
                for meter in account_sensor.meter_entities.values():
                    if meter.entity_id == entity_id:
                        indications = call.data[ATTR_INDICATIONS]
                        if len(indications) != meter.meter.tariff_count:
                            _LOGGER.error('Provided indication count (%d) does not match meter tariff count (%d)'
                                          % (len(indications), meter.meter.tariff_count))
                            return

                        try:
                            # await meter.meter.save_indications(indications)
                            _LOGGER.debug('Submitted indications via service for meter %s (indications: %s)'
                                          % (meter.meter.meter_code, indications))
                            return True

                        except MosenergosbytException as e:
                            _LOGGER.error('API returned error: %s' % e)
                            return

        _LOGGER.error('Entity [%s] is not a registered meter' % entity_id)
        return

    async def async_calculate_indications(call: ServiceCallType):
        # @TODO: stub
        return True

    hass.services.async_register(
        DOMAIN,
        SERVICE_PUSH_INDICATIONS,
        async_push_indications,
        SERVICE_PUSH_INDICATIONS_PAYLOAD_SCHEMA
    )

    # hass.services.async_register(
    #     DOMAIN,
    #     SERVICE_CALCULATE_INDICATIONS,
    #     async_calculate_indications,
    #     SERVICE_CALCULATE_INDICATIONS_PAYLOAD_SCHEMA
    # )


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

        await async_register_services(hass)

        hass.data.setdefault(DATA_UPDATERS, {})[config_entry.entry_id] = \
            async_track_time_interval(hass, update_call, scan_interval)

        new_accounts, new_meters, new_invoices = result

        _LOGGER.info('Set up %d accounts, %d meters and %d invoices, will refresh every %s seconds'
                     % (new_accounts, new_meters, new_invoices, scan_interval.seconds + scan_interval.days*86400))
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
    def __init__(self, account: '_BaseAccount', name_format: str):
        self._state = None
        self._unit = None
        self._attributes = None

        self._name_format = name_format

        self.account: '_BaseAccount' = account
        self.meter_entities: Optional[Dict[str, 'MESMeterSensor']] = None
        self.invoice_entity: Optional['Invoice'] = None

    async def async_update(self):
        """The update method"""
        remaining_days = None

        attributes = {
            'account_code': self.account.account_code,
            'address': self.account.address,
            'service_type': self.account.service_type.name.lower(),
        }

        if not self.account.is_locked:
            try:
                _LOGGER.debug('Updating account %s' % self)
                last_payment = await self.account.get_last_payment()
                current_balance = await self.account.get_current_balance()

                if self.account.service_type == ServiceType.ELECTRICITY:
                    remaining_days = await self.account.get_remaining_days()

            except MosenergosbytException as e:
                message = 'Retrieving data from Mosenergosbyt failed: %s' % e
                if True or _LOGGER.level == logging.DEBUG:
                    _LOGGER.exception(message)
                else:
                    _LOGGER.error(message)
                return False

            attributes.update({
                'last_payment_date': last_payment['date'],
                'last_payment_amount': last_payment['amount'],
                'last_payment_status': last_payment['status'],
                'service_type': self.account.service_type.name.lower(),
                'status': STATE_OK,
            })

            if remaining_days is not None:
                attributes['remaining_days'] = remaining_days

            self._state = current_balance
            self._unit = 'руб.'

        else:
            attributes.update({
                'status': STATE_LOCKED,
                'reason': self.account.lock_reason
            })

            self._state = STATE_UNKNOWN
            self._unit = None

        self._attributes = attributes
        _LOGGER.debug('Update for account %s finished' % self)

    @property
    def name(self):
        """Return the name of the sensor"""
        return self._name_format.format(code=self.account.account_code,
                                        service_name=self.account.service_name,
                                        provider_name=self.account.provider_name)

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
    def __init__(self, meter: '_BaseMeter', name_format: str):
        self._entity_picture = None
        self._state = None
        self._attributes = None
        self._unit = None

        self._icon = 'mdi:counter'

        self._name_format = name_format

        self.meter = meter

    async def async_update(self):
        """The update method"""
        attributes = {
            'account_code': self.meter.account_code,
            'remaining_days': self.meter.remaining_submit_days,
        }

        meter_status = self.meter.current_status

        if isinstance(self.meter, MESElectricityMeter):
            attributes['install_date'] = self.meter.install_date.isoformat()

            for i, value in enumerate(self.meter.last_indications, start=1):
                attributes['last_value_t%d' % i] = value

            for i, value in enumerate(self.meter.submitted_indications, start=1):
                attributes['submitted_value_t%d' % i] = value

        else:
            for key, indication in self.meter.last_indications_dict.items():
                attributes['last_value_%s' % key] = indication[Invoice.ATTRS.VALUE]

                for attribute in [Invoice.ATTRS.NAME, Invoice.ATTRS.COST, Invoice.ATTRS.UNIT]:
                    attributes['last_%s_%s' % (attribute, key)] = indication[attribute]

        self._state = STATE_OK if meter_status is None else meter_status
        self._attributes = attributes

    @property
    def name(self):
        """Return the name of the sensor"""
        return self._name_format.format(code=self.meter.meter_code)

    @property
    def state(self):
        """Return the state of the sensor"""
        return self._state

    @property
    def icon(self):
        """Return the icon of the sensor"""
        return self._icon

    @property
    def device_state_attributes(self):
        """Return the attribute(s) of the sensor"""
        return self._attributes

    @property
    def unique_id(self):
        """Return the unique ID of the sensor"""
        return 'meter_' + str(self.meter.meter_code)

    @property
    def unit_of_measurement(self) -> Optional[str]:
        return self._unit


class MESInvoiceSensor(MESEntity):
    def __init__(self, invoice: 'Invoice', name_format: str):
        self._state = None
        self._attributes = None
        self._name_format = name_format
        self.invoice = invoice

    async def async_update(self):
        """The update method"""
        attributes = {
            'period': self.invoice.period.isoformat(),
            'invoice_id': self.invoice.invoice_id,
            'total': self.invoice.total,
            'paid': self.invoice.paid_amount,
            'initial': self.invoice.initial_balance,
            'charged': self.invoice.charged,
            'insurance': self.invoice.insurance,
            'benefits': self.invoice.benefits,
            'penalty': self.invoice.penalty,
        }

        self._state = round(self.invoice.total, 2)
        self._attributes = attributes

    @property
    def name(self):
        """Return the name of the sensor"""
        return self._name_format.format(code=self.invoice.account.account_code)

    @property
    def state(self):
        """Return the state of the sensor"""
        return self._state

    @property
    def icon(self):
        """Return the icon of the sensor"""
        return 'mdi:receipt'

    @property
    def device_state_attributes(self):
        """Return the attribute(s) of the sensor"""
        return self._attributes

    @property
    def unique_id(self):
        """Return the unique ID of the sensor"""
        return 'invoice_' + str(self.invoice.account.account_code)

    @property
    def unit_of_measurement(self) -> Optional[str]:
        return 'руб.'
