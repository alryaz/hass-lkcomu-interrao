"""
Sensor for Mosenergosbyt cabinet.
Retrieves indications regarding current state of accounts.
"""
import logging
import re
from datetime import date
from enum import IntEnum
from typing import (
    Any,
    ClassVar,
    Dict,
    Hashable,
    Mapping,
    Optional,
    TypeVar,
    Union,
)

import attr as attr
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SERVICE,
    STATE_LOCKED,
    STATE_OK,
    STATE_PROBLEM,
    STATE_UNKNOWN,
)
from homeassistant.helpers.typing import ConfigType

from custom_components.lkcomu_interrao._base import LkcomuEntity, make_common_async_setup_entry
from custom_components.lkcomu_interrao._util import ICONS_FOR_PROVIDERS
from custom_components.lkcomu_interrao.const import (
    ATTR_ACCOUNT_CODE,
    ATTR_ADDRESS,
    ATTR_BENEFITS,
    ATTR_CALL_PARAMS,
    ATTR_CHARGED,
    ATTR_COMMENT,
    ATTR_DESCRIPTION,
    ATTR_FULL_NAME,
    ATTR_IGNORE_INDICATIONS,
    ATTR_IGNORE_PERIOD,
    ATTR_INCREMENTAL,
    ATTR_INDICATIONS,
    ATTR_INITIAL,
    ATTR_INSTALL_DATE,
    ATTR_INSURANCE,
    ATTR_INVOICE_ID,
    ATTR_LAST_SUBMIT_DATE,
    ATTR_LIVING_AREA,
    ATTR_METER_CODE,
    ATTR_MODEL,
    ATTR_NOTIFICATION,
    ATTR_PAID,
    ATTR_PENALTY,
    ATTR_PERIOD,
    ATTR_PROVIDER_NAME,
    ATTR_PROVIDER_TYPE,
    ATTR_REASON,
    ATTR_SERVICE_NAME,
    ATTR_SERVICE_TYPE,
    ATTR_STATUS,
    ATTR_SUBMIT_PERIOD_ACTIVE,
    ATTR_SUBMIT_PERIOD_END,
    ATTR_SUBMIT_PERIOD_START,
    ATTR_SUCCESS,
    ATTR_TOTAL,
    ATTR_TOTAL_AREA,
    CONF_ACCOUNTS,
    CONF_INVOICES,
    CONF_METERS,
    DOMAIN,
    FORMAT_VAR_ID,
    FORMAT_VAR_TYPE_EN,
    FORMAT_VAR_TYPE_RU,
)
from inter_rao_energosbyt.exceptions import EnergosbytException
from inter_rao_energosbyt.interfaces import (
    AbstractAccountWithBalance,
    AbstractAccountWithInvoices,
    AbstractAccountWithMeters,
    AbstractBalance,
    AbstractCalculatableMeter,
    AbstractInvoice,
    AbstractMeter,
    AbstractSubmittableMeter,
    Account,
)
from inter_rao_energosbyt.presets.byt import _AccountWithBytInfo

_LOGGER = logging.getLogger(__name__)

RE_HTML_TAGS = re.compile(r"<[^<]+?>")
RE_MULTI_SPACES = re.compile(r"\s{2,}")


INDICATIONS_MAPPING_SCHEMA = vol.Schema(
    {
        vol.Required(vol.Match(r"t\d+")): cv.positive_float,
    }
)

INDICATIONS_SEQUENCE_SCHEMA = vol.All(
    vol.Any(vol.All(cv.positive_float, cv.ensure_list), [cv.positive_float]),
    lambda x: dict(map(lambda y: ("t" + str(y[0]), y[1]), enumerate(x, start=1))),
)


CALCULATE_PUSH_INDICATIONS_SCHEMA = {
    vol.Required(ATTR_INDICATIONS): vol.Any(
        vol.All(
            cv.string, lambda x: list(map(str.strip, x.split(","))), INDICATIONS_SEQUENCE_SCHEMA
        ),
        INDICATIONS_MAPPING_SCHEMA,
        INDICATIONS_SEQUENCE_SCHEMA,
    ),
    vol.Optional(ATTR_IGNORE_PERIOD, default=False): cv.boolean,
    vol.Optional(ATTR_IGNORE_INDICATIONS, default=False): cv.boolean,
    vol.Optional(ATTR_INCREMENTAL, default=False): cv.boolean,
    vol.Optional(ATTR_NOTIFICATION, default=False): vol.Any(
        cv.boolean,
        persistent_notification.SCHEMA_SERVICE_CREATE,
    ),
}

SERVICE_PUSH_INDICATIONS = "push_indications"
SERVICE_PUSH_INDICATIONS_SCHEMA = CALCULATE_PUSH_INDICATIONS_SCHEMA

SERVICE_CALCULATE_INDICATIONS = "calculate_indications"
SERVICE_CALCULATE_INDICATIONS_SCHEMA = CALCULATE_PUSH_INDICATIONS_SCHEMA

EVENT_CALCULATION_RESULT = DOMAIN + "_calculation_result"
EVENT_PUSH_RESULT = DOMAIN + "_push_result"

FEATURE_PUSH_INDICATIONS = 1
FEATURE_CALCULATE_INDICATIONS = 2

_TLkcomuEntity = TypeVar("_TLkcomuEntity", bound=LkcomuEntity)


class LkcomuAccountSensor(LkcomuEntity[Account]):
    """The class for this sensor"""

    config_key = CONF_ACCOUNTS

    def __init__(self, *args, balance: Optional[AbstractBalance] = None, **kwargs) -> None:
        super().__init__(*args, *kwargs)
        self._balance = balance

        self.entity_id: Optional[
            str
        ] = f"sensor.{self.account_provider_code or 'unknown'}_account_{self.code}"

    @property
    def entity_picture(self) -> Optional[str]:
        account_provider_code = self.account_provider_code
        if account_provider_code is None:
            return None

        provider_icon = ICONS_FOR_PROVIDERS.get(account_provider_code)
        if isinstance(provider_icon, str):
            return provider_icon
        return None

    @property
    def code(self) -> str:
        return self._account.code

    @property
    def device_class(self) -> Optional[str]:
        return DOMAIN + "_account"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor"""
        acc = self._account
        return f"{acc.api.__class__.__name__}_account_{acc.id}"

    @property
    def state(self) -> Union[str, float]:
        if self._account.is_locked:
            return STATE_PROBLEM
        if self._balance is not None:
            return self._balance.balance or 0.0  # fixes -0.0 issues
        return STATE_UNKNOWN

    @property
    def icon(self) -> str:
        return "mdi:flash-circle"

    @property
    def unit_of_measurement(self) -> Optional[str]:
        return "руб."

    @property
    def sensor_related_attributes(self) -> Optional[Mapping[str, Any]]:
        account = self._account
        service_type_value = account.service_type
        service_type = (
            service_type_value.name.lower()
            if isinstance(service_type_value, IntEnum)
            else str(service_type_value)
        )

        provider_type_value = account.provider_type
        provider_type = (
            provider_type_value.name.lower()
            if isinstance(provider_type_value, IntEnum)
            else str(provider_type_value)
        )

        attributes = {
            ATTR_ACCOUNT_CODE: account.code,
            ATTR_ADDRESS: account.address,
            ATTR_DESCRIPTION: account.description,
            ATTR_PROVIDER_TYPE: provider_type,
            ATTR_PROVIDER_NAME: account.provider_name,
            ATTR_SERVICE_TYPE: service_type,
            ATTR_SERVICE_NAME: account.service_name,
        }

        if account.is_locked:
            attributes[ATTR_STATUS] = STATE_LOCKED
            attributes[ATTR_REASON] = account.lock_reason

        else:
            attributes[ATTR_STATUS] = STATE_OK

        if isinstance(account, _AccountWithBytInfo):
            info = account.info
            if info:
                attributes.update(
                    {
                        ATTR_FULL_NAME: info.full_name,
                        ATTR_LIVING_AREA: info.living_area,
                        ATTR_TOTAL_AREA: info.total_area,
                    }
                )

        return attributes

    @property
    def name_format_values(self) -> Mapping[str, Any]:
        """Return the name of the sensor"""
        account = self._account
        return {
            FORMAT_VAR_ID: str(account.id),
            FORMAT_VAR_TYPE_EN: "account",
            FORMAT_VAR_TYPE_RU: "лицевой счёт",
        }

    @classmethod
    async def async_refresh_accounts(
        cls,
        entities: Dict[Hashable, _TLkcomuEntity],
        account: "Account",
        config_entry: ConfigEntry,
        account_config: ConfigType,
    ):
        entity_key = account.id
        try:
            entity = entities[entity_key]
        except KeyError:
            entity = cls(account, account_config)
            entities[entity_key] = entity

            return [entity]
        else:
            if entity.enabled:
                entity.async_schedule_update_ha_state(force_refresh=True)

    async def async_update(self) -> None:
        await self._account.async_update_related()
        if isinstance(self._account, AbstractAccountWithBalance):
            self._balance = await self._account.async_get_balance()


class LkcomuMeterSensor(LkcomuEntity[AbstractAccountWithMeters]):
    """The class for this sensor"""

    config_key: ClassVar[str] = CONF_METERS

    def __init__(self, *args, meter: AbstractMeter, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._meter = meter

        self.entity_id: Optional[
            str
        ] = f"sensor.{self.account_provider_code or 'unknown'}_meter_{self.code}"

    #################################################################################
    # Implementation base of inherent class
    #################################################################################

    @classmethod
    async def async_refresh_accounts(
        cls,
        entities: Dict[Hashable, Optional[_TLkcomuEntity]],
        account: "Account",
        config_entry: ConfigEntry,
        account_config: ConfigType,
    ):
        new_meter_entities = []
        if isinstance(account, AbstractAccountWithMeters):
            meters = await account.async_get_meters()

            for meter_id, meter in meters.items():
                entity_key = (account.id, meter_id)
                try:
                    entity = entities[entity_key]
                except KeyError:
                    entity = cls(
                        account,
                        account_config,
                        meter=meter,
                    )
                    entities[entity_key] = entity
                    new_meter_entities.append(entity)
                else:
                    if entity.enabled:
                        entity.async_schedule_update_ha_state(force_refresh=True)

        return new_meter_entities if new_meter_entities else None

    async def async_update(self) -> None:
        meters = await self._account.async_get_meters()
        meter_data = meters.get(self._meter.id)
        if meter_data is None:
            self.hass.async_create_task(self.async_remove())
        else:
            if isinstance(meter_data, AbstractSubmittableMeter):
                self.platform.async_register_entity_service(
                    SERVICE_PUSH_INDICATIONS,
                    SERVICE_PUSH_INDICATIONS_SCHEMA,
                    "async_push_indications",
                    FEATURE_PUSH_INDICATIONS,
                )

            if isinstance(meter_data, AbstractCalculatableMeter):
                self.platform.async_register_entity_service(
                    SERVICE_CALCULATE_INDICATIONS,
                    SERVICE_CALCULATE_INDICATIONS_SCHEMA,
                    "async_calculate_indications",
                    FEATURE_CALCULATE_INDICATIONS,
                )

            self._meter = meter_data

    #################################################################################
    # Data-oriented implementation of inherent class
    #################################################################################

    @property
    def code(self) -> str:
        return self._meter.code

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor"""
        met = self._meter
        acc = met.account
        return f"{acc.api.__class__.__name__}_meter_{acc.id}_{met.id}"

    @property
    def state(self) -> str:
        return self._meter.status or STATE_OK

    @property
    def icon(self):
        return "mdi:counter"

    @property
    def device_class(self) -> Optional[str]:
        return DOMAIN + "_meter"

    @property
    def supported_features(self) -> int:
        return (
            isinstance(self._meter, AbstractSubmittableMeter) * FEATURE_PUSH_INDICATIONS
            | isinstance(self._meter, AbstractCalculatableMeter) * FEATURE_CALCULATE_INDICATIONS
        )

    @property
    def sensor_related_attributes(self) -> Optional[Mapping[str, Any]]:
        met = self._meter
        attributes = {
            ATTR_METER_CODE: met.code,
            ATTR_ACCOUNT_CODE: met.account.code,
        }

        # Meter model attribute
        model = met.model
        if model:
            attributes[ATTR_MODEL] = model

        # Installation date attribute
        install_date = met.installation_date
        if install_date:
            attributes[ATTR_INSTALL_DATE] = met.installation_date.isoformat()

        # Submission periods attributes
        if isinstance(met, AbstractSubmittableMeter):
            start_date, end_date = met.submission_period
            attributes[ATTR_SUBMIT_PERIOD_START] = start_date.isoformat()
            attributes[ATTR_SUBMIT_PERIOD_END] = end_date.isoformat()
            attributes[ATTR_SUBMIT_PERIOD_ACTIVE] = start_date <= date.today() <= end_date

        last_indications_date = met.last_indications_date
        attributes[ATTR_LAST_SUBMIT_DATE] = (
            None if last_indications_date is None else last_indications_date.isoformat()
        )

        # Add zone information
        for zone_id, zone_def in met.zones.items():
            if attr.has(zone_def.__class__):
                # noinspection PyDataclass
                iterator = attr.asdict(zone_def).items()

            else:
                iterator = (
                    ("name", zone_def.name),
                    ("last_indication", zone_def.last_indication),
                    ("today_indication", zone_def.today_indication),
                )

            for attribute, value in iterator:
                attributes[f"zone_{zone_id}_{attribute}"] = value

        return attributes

    @property
    def name_format_values(self) -> Mapping[str, Any]:
        meter = self._meter
        return {
            FORMAT_VAR_ID: meter.id or "<unknown>",
            FORMAT_VAR_TYPE_EN: "meter",
            FORMAT_VAR_TYPE_RU: "счётчик",
        }

    #################################################################################
    # Additional functionality
    #################################################################################

    def _fire_callback_event(
        self, call_data: Mapping[str, Any], event_data: Mapping[str, Any], event_id: str, title: str
    ):
        meter = self._meter
        hass = self.hass
        comment = event_data.get(ATTR_COMMENT)

        if comment is not None:
            message = str(comment)
            comment = "Response comment: " + str(comment)
        else:
            comment = "Response comment not provided"
            message = comment

        _LOGGER.log(
            logging.INFO if event_data.get(ATTR_SUCCESS) else logging.ERROR,
            RE_MULTI_SPACES.sub(" ", RE_HTML_TAGS.sub("", comment)),
        )

        meter_code = meter.code

        event_data = {
            ATTR_ENTITY_ID: self.entity_id,
            ATTR_METER_CODE: meter_code,
            ATTR_CALL_PARAMS: dict(call_data),
            ATTR_SUCCESS: False,
            ATTR_INDICATIONS: None,
            ATTR_COMMENT: None,
            **event_data,
        }

        _LOGGER.debug("Firing event '%s' with post_fields: %s" % (event_id, event_data))

        hass.bus.async_fire(event_type=event_id, event_data=event_data)

        notification_content: Union[bool, Mapping[str, str]] = call_data[ATTR_NOTIFICATION]

        if notification_content is not False:
            payload = {
                persistent_notification.ATTR_TITLE: title + " - №" + meter_code,
                persistent_notification.ATTR_NOTIFICATION_ID: event_id + "_" + meter_code,
                persistent_notification.ATTR_MESSAGE: message,
            }

            if isinstance(notification_content, Mapping):
                for key, value in notification_content.items():
                    payload[key] = str(value).format_map(event_data)

            hass.async_create_task(
                hass.services.async_call(
                    persistent_notification.DOMAIN,
                    persistent_notification.SERVICE_CREATE,
                    payload,
                )
            )

    def _get_real_indications(self, call_data: Mapping) -> Mapping[str, Union[int, float]]:
        indications: Mapping[str, Union[int, float]] = call_data[ATTR_INDICATIONS]
        meter_zones = self._meter.zones

        for zone_id, new_value in indications.items():
            if zone_id not in meter_zones:
                raise ValueError(f"meter zone {zone_id} does not exist")

        if call_data[ATTR_INCREMENTAL]:
            return {
                zone_id: (
                    (
                        meter_zones[zone_id].today_indication
                        or meter_zones[zone_id].last_indication
                        or 0
                    )
                    + new_value
                )
                for zone_id, new_value in indications.items()
            }

        return indications

    async def async_push_indications(self, **call_data):
        """
        Push indications entity service.
        :param call_data: Parameters for service call
        :return:
        """
        _LOGGER.info(self.log_prefix + "Begin handling indications submission")

        meter = self._meter

        if meter is None:
            raise Exception("Meter is unavailable")

        meter_code = meter.code

        if not isinstance(meter, AbstractSubmittableMeter):
            raise Exception("Meter '%s' does not support indications submission" % (meter_code,))

        else:
            event_data = {}

            try:
                indications = self._get_real_indications(call_data)

                event_data[ATTR_INDICATIONS] = dict(indications)

                await meter.async_submit_indications(
                    **indications,
                    ignore_periods=call_data[ATTR_IGNORE_PERIOD],
                    ignore_values=call_data[ATTR_IGNORE_INDICATIONS],
                )

            except EnergosbytException as e:
                event_data[ATTR_COMMENT] = "API error: %s" % e

            else:
                event_data[ATTR_COMMENT] = "Indications submitted successfully"
                event_data[ATTR_SUCCESS] = True

            finally:
                self._fire_callback_event(
                    call_data,
                    event_data,
                    EVENT_PUSH_RESULT,
                    "Передача показаний",
                )

            _LOGGER.info(self.log_prefix + "End handling indications submission")

            if event_data.get(ATTR_SUCCESS):
                self.async_schedule_update_ha_state(force_refresh=True)
            else:
                raise Exception(event_data[ATTR_COMMENT] or "comment not provided")

    async def async_calculate_indications(self, **call_data):
        meter = self._meter

        if meter is None:
            raise Exception("Meter is unavailable")

        meter_code = meter.code

        _LOGGER.info(self.log_prefix + "Begin handling indications calculation")

        if not isinstance(meter, AbstractCalculatableMeter):
            raise Exception("Meter '%s' does not support indications calculation" % (meter_code,))

        event_data = {ATTR_CHARGED: None, ATTR_SUCCESS: False}

        try:
            indications = self._get_real_indications(call_data)

            event_data[ATTR_INDICATIONS] = dict(indications)

            calculation = await meter.async_calculate_indications(
                **indications,
                ignore_period=call_data[ATTR_IGNORE_PERIOD],
                ignore_indications_check=call_data[ATTR_IGNORE_INDICATIONS],
            )

        except EnergosbytException as e:
            event_data[ATTR_COMMENT] = "Error: %s" % e

        except Exception as e:
            event_data[ATTR_COMMENT] = "Unknown error: %s" % e
            _LOGGER.exception("Unknown error: %s", e)

        else:
            event_data[ATTR_CHARGED] = float(calculation)
            event_data[ATTR_COMMENT] = "Successful calculation"
            event_data[ATTR_SUCCESS] = True

        finally:
            self._fire_callback_event(
                call_data,
                event_data,
                EVENT_CALCULATION_RESULT,
                "Подсчёт показаний",
            )

        _LOGGER.info(self.log_prefix + "End handling indications calculation")

        if event_data.get(ATTR_SUCCESS):
            self.async_schedule_update_ha_state(force_refresh=True)
        else:
            raise Exception(event_data[ATTR_COMMENT] or "comment not provided")


class LkcomuLastInvoiceSensor(LkcomuEntity[AbstractAccountWithInvoices]):
    config_key = CONF_INVOICES

    def __init__(self, *args, last_invoice: Optional["AbstractInvoice"] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._last_invoice = last_invoice

        self.entity_id: Optional[
            str
        ] = f"sensor.{self.account_provider_code or 'unknown'}_last_invoice_{self.code}"

    @property
    def code(self) -> str:
        return self._account.code

    @property
    def device_class(self) -> Optional[str]:
        return DOMAIN + "_invoice"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor"""
        acc = self._account
        return f"{acc.api.__class__.__name__}_lastinvoice_{acc.id}"

    @property
    def state(self) -> Union[float, str]:
        invoice = self._last_invoice
        return round(invoice.total or 0.0, 2) if invoice else STATE_UNKNOWN

    @property
    def icon(self) -> str:
        return "mdi:receipt"

    @property
    def unit_of_measurement(self) -> str:
        return "руб." if self._last_invoice else None

    @property
    def sensor_related_attributes(self):
        invoice = self._last_invoice

        if invoice:
            return {
                ATTR_PERIOD: invoice.period.isoformat(),
                ATTR_INVOICE_ID: invoice.id,
                ATTR_TOTAL: invoice.total,
                ATTR_PAID: invoice.paid,
                ATTR_INITIAL: invoice.initial,
                ATTR_CHARGED: invoice.charged,
                ATTR_INSURANCE: invoice.insurance,
                ATTR_BENEFITS: invoice.benefits,
                ATTR_PENALTY: invoice.penalty,
                ATTR_SERVICE: invoice.service,
            }

        return {}

    @property
    def name_format_values(self) -> Mapping[str, Any]:
        invoice = self._last_invoice
        return {
            FORMAT_VAR_ID: invoice.id if invoice else "<?>",
            FORMAT_VAR_TYPE_EN: "last invoice",
            FORMAT_VAR_TYPE_RU: "последняя квитанция",
        }

    @classmethod
    async def async_refresh_accounts(
        cls,
        entities: Dict[Hashable, _TLkcomuEntity],
        account: "Account",
        config_entry: ConfigEntry,
        account_config: ConfigType,
    ):
        entity_key = account.id
        if isinstance(account, AbstractAccountWithInvoices):
            try:
                entity = entities[entity_key]
            except KeyError:
                entity = cls(account, account_config)
                entities[entity_key] = entity
                return [entity]
            else:
                if entity.enabled:
                    await entity.async_update_ha_state(force_refresh=True)

        return None

    async def async_update(self) -> None:
        self._last_invoice = await self._account.async_get_last_invoice()


async_setup_entry = make_common_async_setup_entry(
    LkcomuAccountSensor,
    LkcomuLastInvoiceSensor,
    LkcomuMeterSensor,
)
