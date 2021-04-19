"""
Sensor for Mosenergosbyt cabinet.
Retrieves values regarding current state of accounts.
"""
import asyncio
import functools
import logging
import re
from datetime import timedelta
from typing import Optional, Tuple, Union, Any, List, Mapping, Type, TypeVar, Set, Iterable, Callable, Dict

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_SCAN_INTERVAL, ATTR_ENTITY_ID, STATE_OK, \
    STATE_LOCKED, STATE_UNKNOWN, ATTR_ATTRIBUTION, ATTR_NAME, ATTR_SERVICE, CONF_ENTITIES
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import HomeAssistantType, ConfigType, StateType
from homeassistant.util.dt import as_local, utcnow

from custom_components.mosenergosbyt.api import API, MosenergosbytException, BaseAccount, \
    Invoice, IndicationsCountException, SubmittableMeter, BaseMeter, MOEGenericMeter, ActionNotSupportedException
from custom_components.mosenergosbyt.const import *

_LOGGER = logging.getLogger(__name__)

RE_INDICATIONS_KEY = re.compile(r'^((t|vl)_?)?(\d+)$')
RE_HTML_TAGS = re.compile(r'<[^<]+?>')
RE_MULTI_SPACES = re.compile(r'\s{2,}')


def indications_validator(indications: Any):
    if isinstance(indications, Mapping):
        temp_indications = {**indications}

        dict_indications = {}

        for key in indications.keys():
            key_str = str(key)
            match = RE_INDICATIONS_KEY.search(key_str)
            if match:
                value = cv.positive_float(indications[key])

                idx = cv.positive_int(match.group(3))
                if idx in dict_indications and dict_indications[idx] != value:
                    raise vol.Invalid('altering indication value for same index: %s' % (idx,), path=[key_str])

                dict_indications[idx] = value
                del temp_indications[key]

        if temp_indications:
            errors = [vol.Invalid('extra keys not allowed', path=[key]) for key in temp_indications.keys()]
            if len(errors) == 1:
                raise errors[0]
            raise vol.MultipleInvalid(errors)

        list_indications = []

        for key in sorted(dict_indications.keys()):
            if len(list_indications) < key - 1:
                raise vol.Invalid('missing indication index: %d' % (key - 1,))
            list_indications.append(dict_indications[key])

    else:
        try:
            indications = map(str.strip, cv.string(indications).split(','))
        except (vol.Invalid, vol.MultipleInvalid):
            indications = cv.ensure_list(indications)

        list_indications = list(map(cv.positive_float, indications))

    if len(list_indications) < 1:
        raise vol.Invalid('empty set of indications provided')

    return list_indications


CALCULATE_PUSH_INDICATIONS_SCHEMA = {
    vol.Required(ATTR_INDICATIONS): indications_validator,
    vol.Optional(ATTR_IGNORE_PERIOD, default=False): cv.boolean,
    vol.Optional(ATTR_IGNORE_INDICATIONS, default=False): cv.boolean,
    vol.Optional(ATTR_INCREMENTAL, default=False): cv.boolean,
    vol.Optional(ATTR_NOTIFICATION, default=False): vol.Any(
        cv.boolean,
        persistent_notification.SCHEMA_SERVICE_CREATE,
    )
}

SERVICE_PUSH_INDICATIONS = 'push_indications'
SERVICE_PUSH_INDICATIONS_PAYLOAD_SCHEMA = CALCULATE_PUSH_INDICATIONS_SCHEMA

SERVICE_CALCULATE_INDICATIONS = 'calculate_indications'
SERVICE_CALCULATE_INDICATIONS_SCHEMA = CALCULATE_PUSH_INDICATIONS_SCHEMA

EVENT_CALCULATION_RESULT = DOMAIN + "_calculation_result"
EVENT_PUSH_RESULT = DOMAIN + "_push_result"


TSensor = TypeVar('TSensor', bound='MESEntity')
DiscoveryReturnType = Tuple[List['MoscowPGUSensor'], List[asyncio.Task]]


def get_remove_tasks(hass: HomeAssistantType, entities: Iterable[Entity]) -> List[asyncio.Task]:
    tasks = []

    for entity in entities:
        if entity.hass is None:
            entity.hass = hass
        tasks.append(
            hass.async_create_task(
                entity.async_remove()
            )
        )

    return tasks


def get_update_function_names(entity_cls: Type['MESEntity']) -> List[str]:
    update_services = []

    for attr_name in dir(entity_cls):
        attr_value = getattr(entity_cls, attr_name)
        if callable(attr_value) and getattr(attr_value, '_segment_update_service', False):
            name = getattr(attr_value, '__name__', None)
            if name:
                update_services.append(name)

    return update_services


def register_update_services(entity_cls: Type['MESEntity'], platform: EntityPlatform) -> None:
    update_function_names = get_update_function_names(entity_cls)

    if update_function_names:
        _LOGGER.debug('Registering %d update services for "%s" entity class',
                      len(update_function_names),
                      entity_cls.__name__)

        for update_function_name in update_function_names:
            service_name = update_function_name

            if service_name.endswith('_all'):
                service_name = service_name[:-4]

            if service_name.startswith('async_'):
                service_name = service_name[6:]

            _LOGGER.info('Registering update service "%s" -> "%s"', service_name, update_function_name)
            platform.async_register_entity_service(service_name, {}, update_function_name,)

    else:
        _LOGGER.debug('No update services for "%s" entity class found',
                      entity_cls.__name__)


async def async_discover_meters(hass: HomeAssistantType,
                                config_entry: ConfigEntry,
                                config: ConfigType,
                                platform: EntityPlatform,
                                existing_entities: Mapping[Type['MESEntity'], List['MESEntity']],
                                name_formats: Mapping[str, Mapping[str, str]],
                                scan_intervals: Mapping[str, Mapping[str, timedelta]],
                                entity_filter: Mapping[str, Mapping[str, bool]],
                                accounts: List['BaseAccount']) -> DiscoveryReturnType:
    entities = []
    tasks = []

    meters_name_formats = name_formats[CONF_METERS]
    meters_scan_intervals = scan_intervals[CONF_METERS]
    meters_entity_filter = entity_filter[CONF_METERS]

    added_entities: Set[MESMeterSensor] = set(existing_entities.get(MESMeterSensor, []))

    meter_lists = await asyncio.gather(*map(lambda account: account.get_meters(), accounts))

    for meters in meter_lists:
        for meter in meters:
            meter_code = meter.meter_code

            if not meters_entity_filter[meter_code]:
                _LOGGER.info('Skipping meter entity "%s" setup/update due to filter', meter_code)
                continue

            meter_entity = None

            for entity in added_entities:
                if entity.meter.meter_code == meter_code:
                    meter_entity = entity
                    break

            if meter_entity is None:
                _LOGGER.info('Setting up meter entity "%s"', meter_code)
                entities.append(
                    MESMeterSensor(
                        name_format=meters_name_formats[meter_code],
                        scan_interval=meters_scan_intervals[meter_code],
                        meter=meter
                    )
                )

            else:
                added_entities.remove(meter_entity)
                if meter_entity.enabled:
                    _LOGGER.debug('Updating meter entity "%s"', meter_code)

                    meter_entity.name_format = meters_name_formats[meter_code]
                    meter_entity.scan_interval = meters_scan_intervals[meter_code]

                    meter_entity.async_schedule_update_ha_state(force_refresh=True)

    if added_entities:
        _LOGGER.info('Removing %d meter entities: "%s"',
                     len(added_entities),
                     '", "'.join([
                         leftover_entity.meter.meter_code
                         for leftover_entity in added_entities
                     ]))

        tasks.extend(get_remove_tasks(hass, added_entities))

    if entities:
        _LOGGER.info('Registering meter services')

        platform.async_register_entity_service(
            SERVICE_CALCULATE_INDICATIONS,
            SERVICE_CALCULATE_INDICATIONS_SCHEMA,
            "async_calculate_indications"
        )

        platform.async_register_entity_service(
            SERVICE_PUSH_INDICATIONS,
            SERVICE_PUSH_INDICATIONS_PAYLOAD_SCHEMA,
            "async_push_indications"
        )

        register_update_services(MESMeterSensor, platform)

    return entities, tasks


async def async_discover_invoices(hass: HomeAssistantType,
                                  config_entry: ConfigEntry,
                                  config: ConfigType,
                                  platform: EntityPlatform,
                                  existing_entities: Mapping[Type['MESEntity'], List['MESEntity']],
                                  name_formats: Mapping[str, Mapping[str, str]],
                                  scan_intervals: Mapping[str, Mapping[str, timedelta]],
                                  entity_filter: Mapping[str, Mapping[str, bool]],
                                  accounts: List['BaseAccount']) -> DiscoveryReturnType:
    entities = []
    tasks = []

    invoices_name_formats = name_formats[CONF_INVOICES]
    invoices_scan_intervals = scan_intervals[CONF_INVOICES]
    invoices_entity_filter = entity_filter[CONF_INVOICES]

    added_entities: Set[MESInvoiceSensor] = set(existing_entities.get(MESInvoiceSensor, []))

    for account in accounts:
        account_code = account.account_code

        if not invoices_entity_filter[account_code]:
            _LOGGER.info('Skipping invoice entity "%s" setup/update due to filter', account_code)
            continue

        invoice_entity = None

        for entity in added_entities:
            if entity.account.account_code == account_code:
                invoice_entity = entity
                break

        if invoice_entity is None:
            _LOGGER.info('Setting up invoice entity "%s"', account_code)
            entities.append(
                MESInvoiceSensor(
                    name_format=invoices_name_formats[account_code],
                    scan_interval=invoices_scan_intervals[account_code],
                    account=account,
                )
            )

        else:
            added_entities.remove(invoice_entity)
            if invoice_entity.enabled:
                _LOGGER.info('Updating invoice entity "%s"', account_code)

                invoice_entity.name_format = invoices_name_formats[account_code]
                invoice_entity.scan_interval = invoices_scan_intervals[account_code]

                invoice_entity.async_schedule_update_ha_state(force_refresh=True)

    if entities:
        register_update_services(MESInvoiceSensor, platform)

    if added_entities:
        _LOGGER.info('Removing %d invoice entities: "%s"',
                     len(added_entities),
                     '", "'.join([
                         leftover_entity.account.account_code
                         for leftover_entity in added_entities
                     ]))

        tasks.extend(get_remove_tasks(hass, added_entities))

    return entities, tasks


async def async_discover_accounts(hass: HomeAssistantType,
                                  config_entry: ConfigEntry,
                                  config: ConfigType,
                                  platform: EntityPlatform,
                                  existing_entities: Mapping[Type['MESEntity'], List['MESEntity']],
                                  name_formats: Mapping[str, Mapping[str, str]],
                                  scan_intervals: Mapping[str, Mapping[str, timedelta]],
                                  entity_filter: Mapping[str, Mapping[str, bool]],
                                  accounts: List['BaseAccount']) -> DiscoveryReturnType:
    entities = []
    tasks = []

    accounts_name_formats = name_formats[CONF_ACCOUNTS]
    accounts_scan_intervals = scan_intervals[CONF_ACCOUNTS]
    accounts_entity_filter = entity_filter[CONF_ACCOUNTS]

    added_entities: Set[MESAccountSensor] = set(existing_entities.get(MESAccountSensor, []))

    for account in accounts:
        account_code = account.account_code

        if not accounts_entity_filter[account_code]:
            _LOGGER.info('Skipping account entity "%s" setup/update due to filter', account_code)
            continue

        account_entity = None

        for entity in added_entities:
            if entity.account.account_code == account_code:
                account_entity = entity
                break

        if account_entity is None:
            _LOGGER.info('Setting up account entity "%s"', account_code)
            entities.append(
                MESAccountSensor(
                    name_format=accounts_name_formats[account_code],
                    scan_interval=accounts_scan_intervals[account_code],
                    account=account,
                )
            )

        else:
            added_entities.remove(account_entity)
            if account_entity.enabled:
                _LOGGER.info('Updating account entity "%s"', account_code)

                account_entity.name_format = accounts_name_formats[account_code]
                account_entity.scan_interval = accounts_scan_intervals[account_code]

                # This way account object is re-used
                tasks.append(
                    hass.async_create_task(
                        account_entity.async_update_all(
                            write_ha_state=True,
                            account=account,
                        )
                    )
                )

    if entities:
        register_update_services(MESAccountSensor, platform)

    if added_entities:
        _LOGGER.info('Removing %d account entities: "%s"',
                     len(added_entities),
                     '", "'.join([
                         leftover_entity.account.account_code
                         for leftover_entity in added_entities
                     ]))

        tasks.extend(get_remove_tasks(hass, added_entities))

    return entities, tasks


async def async_discover(hass: HomeAssistantType, config_entry: ConfigEntry,
                         user_cfg: ConfigType, async_add_devices: Callable[[List[Entity], bool], Any]) -> None:
    api: Optional[API] = hass.data.get(DATA_API_OBJECTS, {}).get(config_entry.entry_id)

    if api is None:
        _LOGGER.error('API object not yet present')
        raise PlatformNotReady

    platform = entity_platform.current_platform.get()

    if platform is None:
        _LOGGER.error('Entity platform is empty')
        raise PlatformNotReady

    # Fetch necessary data: Accounts
    accounts = await api.get_accounts(return_unsupported_accounts=False, suppress_unsupported_logging=True)

    # Account post-fetch filtering
    if CONF_FILTER in user_cfg:
        accounts_filter = user_cfg[CONF_FILTER]
        accounts = [account for account in accounts if accounts_filter[account.account_code]]

    # Prepare entity discovery call arguments
    existing_entities = hass.data.get(DATA_ENTITIES, {}).get(config_entry.entry_id, {})
    scan_intervals = user_cfg[CONF_SCAN_INTERVAL]
    name_formats = user_cfg[CONF_NAME_FORMAT]
    entity_filter = user_cfg[CONF_ENTITIES]

    # Execute entity discovery calls
    tasks = [
        hass.async_create_task(
            async_discover_func(
                hass=hass,
                config_entry=config_entry,
                config=user_cfg,
                platform=platform,
                existing_entities=existing_entities,
                name_formats=name_formats,
                scan_intervals=scan_intervals,
                entity_filter=entity_filter,
                accounts=accounts,
            )
        )
        for async_discover_func in (async_discover_accounts, async_discover_invoices, async_discover_meters)
    ]

    await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

    # Collect new entities and internal tasks
    new_entities = []
    new_tasks = []

    for task in tasks:
        entities, tasks = task.result()
        new_entities.extend(entities)
        new_tasks.extend(tasks)

    # Wait until internal tasks are complete (if present)
    if new_tasks:
        await asyncio.wait(tasks)

    # Add new entities to HA registry (if present)
    if new_entities:
        async_add_devices(new_entities, True)

    _LOGGER.debug('Entity discovery complete for username "%s"', user_cfg[CONF_USERNAME])


async def async_setup_entry(hass: HomeAssistantType, config_entry: ConfigEntry, async_add_devices):
    username = config_entry.data[CONF_USERNAME]

    user_cfg = hass.data.get(DATA_FINAL_CONFIG, {}).get(username)

    if user_cfg is None:
        _LOGGER.error('Final configuration not yet present')
        raise PlatformNotReady

    username = user_cfg[CONF_USERNAME]

    _LOGGER.debug('Setting up entry for username "%s" from sensors' % username)

    await async_discover(
        hass=hass,
        config_entry=config_entry,
        user_cfg=user_cfg,
        async_add_devices=async_add_devices
    )


class NameFormatDict(dict):
    def __missing__(self, key):
        return '{{' + str(key) + '}}'


class MESEntity(Entity):
    def __init__(self, name_format: str, scan_interval: timedelta):
        self.name_format = name_format
        self.scan_interval = scan_interval
        self.entity_updater: Optional[Callable[[], Any]] = None
        self._update_counters: Dict[str, int] = {}

    @staticmethod
    def wrap_update_segment(fn: Callable):
        segment = fn.__name__ or 'unknown'
        if segment.startswith('async_'):
            segment = segment[6:]
        if segment.startswith('update_'):
            segment = segment[7:]

        @functools.wraps(fn)
        async def _internal(self: MESEntity, *args, write_ha_state: bool = True, **kwargs):
            counter = self._update_counters.get(segment, 0) + 1
            self._update_counters[segment] = counter

            _LOGGER.info(self._log_prefix + 'Begin updating "%s" segment (%d)', segment, counter)

            result = await fn(self, *args, **kwargs)

            _LOGGER.info(self._log_prefix + 'Finished updating "%s" segment (%d)', segment, counter)

            if write_ha_state:
                self.async_write_ha_state()
                self.restart_updater()

            return result

        setattr(_internal, '_segment_update_service', True)

        return _internal

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.

        False if entity pushes its state to HA.
        """
        return False

    @property
    def device_state_attributes(self):
        """Return the attribute(s) of the sensor"""
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            **(self.sensor_related_attributes or {})
        }

    @property
    def _log_prefix(self):
        return ('[%s][%s] ' % (self.device_class.replace(DOMAIN + '_', '', 1), self.code)).replace('%', '%%')

    def _log_unsupported(self, action: str, attribute: str, exception: Exception):
        message = 'Did not add %s (attribute: %s)' % (action, attribute)
        if exception.args:
            message += ' (reason: %s)' % (exception,)
        _LOGGER.debug(self._log_prefix + message)

    @property
    def name(self) -> Optional[str]:
        name_format_values = NameFormatDict({
            key: ('' if value is None else value)
            for key, value in self.name_format_values.items()
        })
        return self.name_format.format_map(name_format_values)

    @property
    def state(self) -> StateType:
        raise NotImplementedError

    @property
    def icon(self) -> str:
        raise NotImplementedError

    @property
    def sensor_related_attributes(self) -> Optional[Mapping[str, Any]]:
        raise NotImplementedError

    @property
    def name_format_values(self) -> Mapping[str, Any]:
        raise NotImplementedError

    @property
    def unique_id(self) -> str:
        raise NotImplementedError

    @property
    def code(self) -> str:
        raise NotImplementedError

    @property
    def device_class(self) -> Optional[str]:
        raise NotImplementedError

    async def async_added_to_hass(self) -> None:
        _LOGGER.info(self._log_prefix + 'Adding to HomeAssistant')
        entities = self.hass.data\
            .setdefault(DATA_ENTITIES, {})\
            .setdefault(self.registry_entry.config_entry_id, {})\
            .setdefault(self.__class__, [])

        if self not in entities:
            entities.append(self)

        self.restart_updater()

    async def async_will_remove_from_hass(self) -> None:
        _LOGGER.info(self._log_prefix + 'Removing from HomeAssistant')
        self.stop_updater()

        entities = self.hass.data\
            .get(DATA_ENTITIES, {})\
            .get(self.registry_entry.config_entry_id, {})\
            .get(self.__class__, [])

        if self in entities:
            entities.remove(self)

    def stop_updater(self) -> None:
        if self.entity_updater is not None:
            _LOGGER.info(self._log_prefix + 'Stopping updater')
            self.entity_updater()
            self.entity_updater = None

    def restart_updater(self) -> None:
        self.stop_updater()

        def _update_entity(*_):
            nonlocal self
            self.async_schedule_update_ha_state(force_refresh=True)

        _LOGGER.info(self._log_prefix + 'Starting updater (interval: %s seconds, next call: %s)',
                     self.scan_interval.total_seconds(), as_local(utcnow()) + self.scan_interval)
        self.entity_updater = async_track_time_interval(self.hass, _update_entity, self.scan_interval)

    async def async_update(self) -> None:
        self.stop_updater()
        try:
            # noinspection PyArgumentList
            await self.async_update_all(write_ha_state=False)
        finally:
            self.restart_updater()

    async def async_update_all(self) -> None:
        raise NotImplementedError


class MESAccountSensor(MESEntity):
    """The class for this sensor"""

    def __init__(self, *args, account: 'BaseAccount', current_balance: Optional[float] = None,
                 last_payment: Optional[Mapping[str, Any]] = None,
                 submission_availability: Optional[Tuple[bool, int]] = None,
                 **kwargs):
        super().__init__(*args, **kwargs)

        self.account = account
        self.current_balance = current_balance
        self.last_payment = last_payment
        self.submission_availability = submission_availability

    @property
    def code(self) -> str:
        return self.account.account_code

    @property
    def device_class(self) -> Optional[str]:
        return DOMAIN + '_account'

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor"""
        return 'ls_' + str(self.account.service_id)

    @property
    def state(self) -> Union[str, float]:
        if self.account.is_locked:
            return STATE_LOCKED
        if self.current_balance is not None:
            return self.current_balance or 0.0
        return STATE_UNKNOWN

    @property
    def icon(self) -> str:
        return 'mdi:flash-circle'

    @property
    def unit_of_measurement(self) -> Optional[str]:
        if isinstance(self.state, float):
            return 'руб.'

    @property
    def sensor_related_attributes(self) -> Optional[Mapping[str, Any]]:
        account = self.account

        attributes = {
            ATTR_ACCOUNT_CODE: account.account_code,
            ATTR_ADDRESS: account.address,
            ATTR_SERVICE_TYPE: account.service_type.name.lower(),
            ATTR_DESCRIPTION: account.description,
            ATTR_PROVIDER_NAME: account.provider_name,
            ATTR_SERVICE_NAME: account.service_name,
        }

        if account.is_locked:
            attributes[ATTR_STATUS] = STATE_LOCKED
            attributes[ATTR_REASON] = account.lock_reason

        else:
            attributes[ATTR_STATUS] = STATE_OK

        last_payment = self.last_payment or {}
        attributes[ATTR_LAST_PAYMENT_DATE] = last_payment.get('date')
        attributes[ATTR_LAST_PAYMENT_AMOUNT] = last_payment.get('amount')
        attributes[ATTR_LAST_PAYMENT_STATUS] = last_payment.get('status', STATE_UNKNOWN)

        submission_availability = self.submission_availability or (None, None)
        attributes[ATTR_SUBMIT_PERIOD_ACTIVE] = submission_availability[0]
        attributes[ATTR_REMAINING_DAYS] = submission_availability[1]

        return attributes

    @property
    def name_format_values(self) -> Mapping[str, Any]:
        """Return the name of the sensor"""
        return {
            'type': 'account',
            'code': self.account.account_code,
            'service_name': self.account.service_name,
            'service_id': self.account.service_id,
            'service_type_id': self.account.service_type,
            'service_type_name': self.account.service_type.name,
            'provider_name': self.account.provider_name,
        }

    @MESEntity.wrap_update_segment
    async def async_update_account(self, account: Optional[BaseAccount] = None) -> None:
        if account is None:
            accounts = await self.account.api.get_accounts(suppress_unsupported_logging=True)
            account_code = self.account.account_code

            for updated_account in accounts:
                if updated_account.account_code == account_code:
                    account = updated_account
                    break

            if account is None:
                raise Exception('could not update account "%s"' % (self.account.account_code,))

        self.account = account

    @MESEntity.wrap_update_segment
    async def async_update_last_payment(
            self,
            last_payment: Optional[Mapping[str, Any]] = None
    ) -> None:
        if last_payment is None:
            last_payment = await self.account.get_last_payment()

        self.last_payment = last_payment

    @MESEntity.wrap_update_segment
    async def async_update_current_balance(
            self,
            current_balance: Optional[float] = None
    ) -> None:
        if current_balance is None:
            current_balance = await self.account.get_current_balance()

        self.current_balance = current_balance

    @MESEntity.wrap_update_segment
    async def async_update_submission_availability(
            self,
            submission_availability: Optional[Tuple[bool, int]] = None
    ) -> None:
        if submission_availability is None:
            submission_availability = await self.account.get_submission_availability()

        self.submission_availability = submission_availability

    @MESEntity.wrap_update_segment
    async def async_update_all(
            self,
            account: Optional[BaseAccount] = None,
            last_payment: Optional[Mapping[str, Any]] = None,
            current_balance: Optional[float] = None,
            submission_availability: Optional[Tuple[bool, int]] = None
    ) -> None:
        """The update method"""
        # Fetch recent account information first (to ensure account availability)
        await self.async_update_account(account, write_ha_state=False)

        await asyncio.wait(map(self.hass.async_create_task, (
            self.async_update_last_payment(last_payment, write_ha_state=False),
            self.async_update_current_balance(current_balance, write_ha_state=False),
            self.async_update_submission_availability(submission_availability, write_ha_state=False),
        )))


class MESMeterSensor(MESEntity):
    """The class for this sensor"""

    def __init__(self, *args, meter: 'BaseMeter', **kwargs):
        super().__init__(*args, **kwargs)

        self.meter = meter

    @property
    def code(self) -> str:
        return self.meter.meter_code

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor"""
        return 'meter_' + self.meter.meter_code

    @property
    def state(self) -> str:
        meter_status = self.meter.current_status
        if meter_status:
            return meter_status
        return STATE_OK

    @property
    def icon(self):
        if isinstance(self.meter, MOEGenericMeter):
            return 'mdi:gauge'
        return 'mdi:counter'

    @property
    def device_class(self) -> Optional[str]:
        return DOMAIN + '_meter'

    @property
    def sensor_related_attributes(self) -> Optional[Mapping[str, Any]]:
        attributes = {
            ATTR_METER_CODE: self.meter.meter_code,
            ATTR_ACCOUNT_CODE: self.meter.account_code,
        }

        # Meter model attribute
        model = self.meter.model
        if model:
            attributes[ATTR_MODEL] = model

        # Installation date attribute
        install_date = self.meter.install_date
        if install_date:
            attributes[ATTR_INSTALL_DATE] = self.meter.install_date.isoformat()

        # Submit period attributes
        try:
            submit_period_start = self.meter.period_start_date
        except (ActionNotSupportedException, NotImplementedError) as e:
            self._log_unsupported('submit period start date', ATTR_SUBMIT_PERIOD_START, e)
        else:
            if submit_period_start:
                attributes[ATTR_SUBMIT_PERIOD_START] = submit_period_start.isoformat()

        try:
            submit_period_end = self.meter.period_end_date
        except (ActionNotSupportedException, NotImplementedError) as e:
            self._log_unsupported('submit period end date', ATTR_SUBMIT_PERIOD_END, e)
        else:
            if submit_period_end:
                attributes[ATTR_SUBMIT_PERIOD_END] = submit_period_end.isoformat()

        # Add tariff data
        try:
            tariffs = self.meter.tariffs
        except (ActionNotSupportedException, NotImplementedError) as e:
            self._log_unsupported('tariffs and indications', 'tariff_[tariff ID]_[key]', e)
        else:
            for tariff in tariffs:
                for key, value in {
                    ATTR_NAME: tariff.name,
                    ATTR_COST: tariff.cost,
                    ATTR_DESCRIPTION: tariff.description,
                    ATTR_UNIT: tariff.unit
                }.items():
                    if value is not None:
                        attributes['tariff_%s_%s' % (tariff.id, key)] = value

        # Add last indications date
        try:
            last_submission_date = self.meter.last_indications_date
        except (ActionNotSupportedException, NotImplementedError) as e:
            self._log_unsupported('last submission date', ATTR_LAST_SUBMIT_DATE, e)
        else:
            last_submission_date = None if last_submission_date is None else last_submission_date.isoformat()
            attributes[ATTR_LAST_SUBMIT_DATE] = last_submission_date

        # Add indications values
        try:
            tariff_ids = self.meter.tariff_ids
        except (ActionNotSupportedException, NotImplementedError) as e:
            self._log_unsupported('indications', '(last|today|submitted)_value_[tariff ID]', e)
        else:
            if tariff_ids:
                # Add last indications (if available)
                try:
                    last_indications = self.meter.last_indications
                except (ActionNotSupportedException, NotImplementedError) as e:
                    self._log_unsupported('last indications\' values', ATTR_FMT_LAST_VALUE % '[tariff ID]', e)
                else:
                    for tariff_id, value in zip(tariff_ids, last_indications):
                        attributes[ATTR_FMT_LAST_VALUE % tariff_id] = value
        
                # Add submitted indications (if available)
                try:
                    submitted_indications = self.meter.submitted_indications
                except (ActionNotSupportedException, NotImplementedError) as e:
                    self._log_unsupported('submitted indications\' values', ATTR_FMT_SUBMITTED_VALUE % '[tariff ID]', e)
                else:
                    for tariff_id, value in zip(tariff_ids, submitted_indications):
                        attributes[ATTR_FMT_SUBMITTED_VALUE % tariff_id] = value
        
                # Add today's indications (if available)
                try:
                    today_indications = self.meter.today_indications
                except (ActionNotSupportedException, NotImplementedError) as e:
                    self._log_unsupported('today\'s indications\' values', ATTR_FMT_TODAY_VALUE % '[tariff ID]', e)
                else:
                    for tariff_id, value in zip(tariff_ids, today_indications):
                        attributes[ATTR_FMT_TODAY_VALUE % tariff_id] = value
        
                return attributes

    @property
    def name_format_values(self) -> Mapping[str, Any]:
        return {
            'type': 'meter',
            'code': self.meter.meter_code,
            'account_code': self.meter.account_code,
            'model': self.meter.model or 'unknown',
        }

    @MESEntity.wrap_update_segment
    async def async_update_meter(self, meter: Optional[BaseMeter] = None) -> None:
        if meter is None:
            meters = await self.meter.account.get_meters()
            meter_code = self.meter.meter_code

            for updated_meter in meters:
                if updated_meter.meter_code == meter_code:
                    meter = updated_meter
                    break

            if meter is None:
                raise Exception('Could not update meter entity: not meter found')

        self.meter = meter

    @MESEntity.wrap_update_segment
    async def async_update_all(self, meter: Optional[BaseMeter] = None) -> None:
        await self.async_update_meter(meter, write_ha_state=False)

    def _fire_callback_event(self, call_data: Mapping[str, Any], event_data: Mapping[str, Any], event_id: str,
                             title: str):
        comment = event_data.get(ATTR_COMMENT)
        if comment is not None:
            message = str(comment)
            comment = 'Response comment: ' + str(comment)
        else:
            comment = 'Response comment not provided'
            message = comment

        _LOGGER.log(
            logging.INFO if event_data.get(ATTR_SUCCESS) else logging.ERROR,
            RE_MULTI_SPACES.sub(' ', RE_HTML_TAGS.sub('', comment))
        )

        event_data = {
            ATTR_ENTITY_ID: self.entity_id,
            ATTR_METER_CODE: self.meter.meter_code,
            ATTR_CALL_PARAMS: dict(call_data),
            ATTR_SUCCESS: False,
            ATTR_INDICATIONS: None,
            ATTR_INDICATIONS_DICT: None,
            ATTR_COMMENT: None,
            **event_data,
        }

        if event_data.get(ATTR_INDICATIONS_DICT) is None and event_data[ATTR_INDICATIONS]:
            event_data[ATTR_INDICATIONS_DICT] = {
                't%d' % i: v
                for i, v in enumerate(event_data[ATTR_INDICATIONS], start=1)
            }

        _LOGGER.debug("Firing event '%s' with data: %s" % (event_id, event_data))

        self.hass.bus.async_fire(
            event_type=event_id,
            event_data=event_data
        )

        notification_content: Union[bool, Mapping[str, str]] = call_data[ATTR_NOTIFICATION]

        if notification_content is not False:
            meter_code = str(self.meter.meter_code)

            payload = {
                persistent_notification.ATTR_TITLE: title + ' - №' + meter_code,
                persistent_notification.ATTR_NOTIFICATION_ID: event_id + "_" + meter_code,
                persistent_notification.ATTR_MESSAGE: message,
            }

            if isinstance(notification_content, Mapping):
                for key, value in notification_content.items():
                    payload[key] = str(value).format_map(event_data)

            self.hass.async_create_task(
                self.hass.services.async_call(
                    persistent_notification.DOMAIN,
                    persistent_notification.SERVICE_CREATE,
                    payload,
                )
            )

    def _get_real_indications(self, call_data: Mapping) -> List[Union[int, float]]:
        if call_data[ATTR_INCREMENTAL]:
            return [
                a + (s or l or 0)
                for a, l, s in zip(
                    call_data[ATTR_INDICATIONS],
                    self.meter.last_indications,
                    self.meter.submitted_indications,
                )
            ]

        return call_data[ATTR_INDICATIONS]

    async def async_push_indications(self, **call_data):
        """
        Push indications entity service.
        :param call_data: Parameters for service call
        :return:
        """
        _LOGGER.info(self._log_prefix + 'Begin handling indications submission')

        meter_code = self.meter.meter_code

        if not isinstance(self.meter, SubmittableMeter):
            raise Exception('Meter \'%s\' does not support indications submission' % (meter_code,))

        else:
            event_data = {}

            try:
                indications = self._get_real_indications(call_data)

                event_data[ATTR_INDICATIONS] = indications

                comment = await self.meter.submit_indications(
                    indications,
                    ignore_period_check=call_data[ATTR_IGNORE_PERIOD],
                    ignore_indications_check=call_data[ATTR_IGNORE_INDICATIONS],
                )

            except IndicationsCountException as e:
                event_data[ATTR_COMMENT] = 'Error: %s' % e

            except MosenergosbytException as e:
                event_data[ATTR_COMMENT] = 'API returned error: %s' % e

            else:
                event_data[ATTR_COMMENT] = comment
                event_data[ATTR_SUCCESS] = True

            finally:
                self._fire_callback_event(call_data, event_data, EVENT_PUSH_RESULT, 'Передача показаний')

            _LOGGER.info(self._log_prefix + 'End handling indications submission')

            if not event_data.get(ATTR_SUCCESS):
                raise Exception(event_data[ATTR_COMMENT] or 'comment not provided')

    async def async_calculate_indications(self, **call_data):
        meter_code = self.meter.meter_code

        _LOGGER.info(self._log_prefix + 'Begin handling indications calculation')

        if not isinstance(self.meter, SubmittableMeter):
            raise Exception('Meter \'%s\' does not support indications calculation' % (meter_code,))

        event_data = {ATTR_PERIOD: None, ATTR_CHARGED: None, ATTR_CORRECT: None}

        try:
            indications = self._get_real_indications(call_data)

            event_data[ATTR_INDICATIONS] = indications

            calculation = await self.meter.calculate_indications(
                indications,
                ignore_period_check=call_data[ATTR_IGNORE_PERIOD],
                ignore_indications_check=call_data[ATTR_IGNORE_INDICATIONS],
            )

        except IndicationsCountException as e:
            event_data[ATTR_COMMENT] = 'Error: %s' % e

        except MosenergosbytException as e:
            event_data[ATTR_COMMENT] = 'API returned error: %s' % e

        except Exception as e:
            event_data[ATTR_COMMENT] = 'Unknown error: %s' % e
            _LOGGER.exception('Unknown error: %s', e)

        else:
            event_data[ATTR_SUCCESS] = True
            event_data[ATTR_COMMENT] = calculation.comment
            event_data[ATTR_PERIOD] = str(calculation.period)
            event_data[ATTR_CHARGED] = calculation.charged
            event_data[ATTR_CORRECT] = calculation.correct

        finally:
            self._fire_callback_event(call_data, event_data, EVENT_CALCULATION_RESULT, 'Подсчёт показаний')

        _LOGGER.info(self._log_prefix + 'End handling indications calculation')

        if not event_data.get(ATTR_SUCCESS):
            raise Exception(event_data[ATTR_COMMENT] or 'comment not provided')


class MESInvoiceSensor(MESEntity):
    def __init__(self, *args, account: BaseAccount, invoice: Optional['Invoice'] = None, **kwargs):
        super().__init__(*args, **kwargs)

        self.account = account
        self.invoice = invoice

    @property
    def code(self) -> str:
        return self.account.account_code

    @property
    def device_class(self) -> Optional[str]:
        return DOMAIN + '_invoice'

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor"""
        return 'invoice_' + self.account.account_code

    @property
    def state(self) -> Union[float, str]:
        return round(self.invoice.total or 0.0, 2) if self.invoice else STATE_UNKNOWN

    @property
    def icon(self) -> str:
        return 'mdi:receipt'

    @property
    def unit_of_measurement(self) -> Optional[str]:
        return 'руб.' if self.invoice else None

    @property
    def sensor_related_attributes(self):
        invoice = self.invoice

        if invoice:
            return {
                ATTR_PERIOD: invoice.period.isoformat(),
                ATTR_INVOICE_ID: invoice.invoice_id,
                ATTR_TOTAL: invoice.total,
                ATTR_PAID: invoice.paid_amount,
                ATTR_INITIAL: invoice.initial_balance,
                ATTR_CHARGED: invoice.charged,
                ATTR_INSURANCE: invoice.insurance,
                ATTR_BENEFITS: invoice.benefits,
                ATTR_PENALTY: invoice.penalty,
                ATTR_SERVICE: invoice.service,
            }

        else:
            return {
                ATTR_PERIOD: None,
                ATTR_INVOICE_ID: None,
                ATTR_TOTAL: None,
            }

    @property
    def name_format_values(self) -> Mapping[str, Any]:
        return {
            'type': 'invoice',
            'code': self.account.account_code,
            'account_code': self.account.account_code,
        }

    @MESEntity.wrap_update_segment
    async def async_update_invoice(self, invoice: Optional['Invoice'] = None) -> None:
        if invoice is None:
            invoice = await self.account.get_last_invoice()

        self.invoice = invoice

    @MESEntity.wrap_update_segment
    async def async_update_all(self, invoice: Optional['Invoice'] = None):
        await self.async_update_invoice(invoice, write_ha_state=False)
