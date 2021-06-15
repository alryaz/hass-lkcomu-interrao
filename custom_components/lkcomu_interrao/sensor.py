"""
Sensor for Mosenergosbyt cabinet.
Retrieves indications regarding current state of accounts.
"""
import asyncio
import logging
import re
from datetime import date, timedelta
from enum import IntEnum
from typing import (
    Any,
    Dict,
    Hashable,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
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
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.helpers.typing import ConfigType

from custom_components.lkcomu_interrao._base import MESEntity, make_common_async_setup_entry
from custom_components.lkcomu_interrao.const import (
    ATTR_ACCOUNT_CODE,
    ATTR_ADDRESS,
    ATTR_BENEFITS,
    ATTR_CALL_PARAMS,
    ATTR_CHARGED,
    ATTR_COMMENT,
    ATTR_DESCRIPTION,
    ATTR_IGNORE_INDICATIONS,
    ATTR_IGNORE_PERIOD,
    ATTR_INCREMENTAL,
    ATTR_INDICATIONS,
    ATTR_INDICATIONS_DICT,
    ATTR_INITIAL,
    ATTR_INSTALL_DATE,
    ATTR_INSURANCE,
    ATTR_INVOICE_ID,
    ATTR_LAST_SUBMIT_DATE,
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
    CONF_ACCOUNTS,
    CONF_INVOICES,
    CONF_METERS,
    CONF_NAME_FORMAT,
    DOMAIN,
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

RE_INDICATIONS_KEY = re.compile(r"^((t|vl)_?)?(\d+)$")
RE_HTML_TAGS = re.compile(r"<[^<]+?>")
RE_MULTI_SPACES = re.compile(r"\s{2,}")


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
                    raise vol.Invalid(
                        "altering indication value for same index: %s" % (idx,), path=[key_str]
                    )

                dict_indications[idx] = value
                del temp_indications[key]

        if temp_indications:
            errors = [
                vol.Invalid("extra keys not allowed", path=[key]) for key in temp_indications.keys()
            ]
            if len(errors) == 1:
                raise errors[0]
            raise vol.MultipleInvalid(errors)

        list_indications = []

        for key in sorted(dict_indications.keys()):
            if len(list_indications) < key - 1:
                raise vol.Invalid("missing indication index: %d" % (key - 1,))
            list_indications.append(dict_indications[key])

    else:
        try:
            indications = map(str.strip, cv.string(indications).split(","))
        except (vol.Invalid, vol.MultipleInvalid):
            indications = cv.ensure_list(indications)

        list_indications = list(map(cv.positive_float, indications))

    if len(list_indications) < 1:
        raise vol.Invalid("empty set of indications provided")

    return list_indications


CALCULATE_PUSH_INDICATIONS_SCHEMA = {
    vol.Required(ATTR_INDICATIONS): indications_validator,
    vol.Optional(ATTR_IGNORE_PERIOD, default=False): cv.boolean,
    vol.Optional(ATTR_IGNORE_INDICATIONS, default=False): cv.boolean,
    vol.Optional(ATTR_INCREMENTAL, default=False): cv.boolean,
    vol.Optional(ATTR_NOTIFICATION, default=False): vol.Any(
        cv.boolean,
        persistent_notification.SCHEMA_SERVICE_CREATE,
    ),
}

SERVICE_PUSH_INDICATIONS = "push_indications"
SERVICE_PUSH_INDICATIONS_PAYLOAD_SCHEMA = CALCULATE_PUSH_INDICATIONS_SCHEMA

SERVICE_CALCULATE_INDICATIONS = "calculate_indications"
SERVICE_CALCULATE_INDICATIONS_SCHEMA = CALCULATE_PUSH_INDICATIONS_SCHEMA

EVENT_CALCULATION_RESULT = DOMAIN + "_calculation_result"
EVENT_PUSH_RESULT = DOMAIN + "_push_result"


TSensor = TypeVar("TSensor", bound="MESEntity")
DiscoveryReturnType = Tuple[List["MoscowPGUSensor"], List[asyncio.Task]]


_TMESEntity = TypeVar("_TMESEntity", bound="MESEntity")


class MESAccountSensor(MESEntity[AbstractAccountWithBalance, AbstractBalance]):
    """The class for this sensor"""

    config_key = CONF_ACCOUNTS

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
            return STATE_LOCKED
        if self._entity_data is not None:
            return float(self._entity_data) or 0.0
        return STATE_UNKNOWN

    @property
    def icon(self) -> str:
        return "mdi:flash-circle"

    @property
    def unit_of_measurement(self) -> Optional[str]:
        if self._entity_data is not None:
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
                        "full_name": info.full_name,
                        "living_area": info.living_area,
                        "total_area": info.total_area,
                    }
                )

        return attributes

    @property
    def name_format_values(self) -> Mapping[str, Any]:
        """Return the name of the sensor"""
        account = self._account
        return {
            "code": account.code,
            "id": account.id,
            "provider_name": account.provider_name,
            "service_name": account.service_name,
            "service_type_value": int(account.service_type),
            "type": "account",
        }

    @classmethod
    async def async_refresh_accounts(
        cls: Type[_TMESEntity],
        entities: Dict[Hashable, Optional[_TMESEntity]],
        account: "Account",
        config_entry: ConfigEntry,
        final_config: ConfigType,
    ) -> Optional[Iterable[_TMESEntity]]:
        entity_key = account.id
        try:
            entity = entities[entity_key]
        except KeyError:
            entity = cls(
                final_config[CONF_NAME_FORMAT][cls.config_key][account.code],
                timedelta(hours=1),
                account,
            )
            entities[entity_key] = entity
            return [entity]
        else:
            if entity.enabled:
                entity.async_schedule_update_ha_state(force_refresh=True)

    async def async_update(self) -> None:
        await self._account.async_update_related()
        self._entity_data = await self._account.async_get_balance()


class MESMeterSensor(MESEntity[AbstractAccountWithMeters, AbstractMeter]):
    """The class for this sensor"""

    config_key = CONF_METERS

    @property
    def code(self) -> str:
        return self._entity_updater.code

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor"""
        met = self._entity_data
        acc = met.account
        return f"{acc.api.__class__.__name__}_meter_{acc.id}_{met.id}"

    @property
    def state(self) -> str:
        return self._entity_data.status or STATE_OK

    @property
    def icon(self):
        return "mdi:counter"

    @property
    def device_class(self) -> Optional[str]:
        return DOMAIN + "_meter"

    @property
    def sensor_related_attributes(self) -> Optional[Mapping[str, Any]]:
        met = self._entity_data
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
        meter = self._entity_data
        return {
            "type": "calculated_for",
            "code": meter.code,
            "account_code": meter.code,
            "model": meter.model or "unknown",
        }

    def _fire_callback_event(
        self, call_data: Mapping[str, Any], event_data: Mapping[str, Any], event_id: str, title: str
    ):
        meter = self._entity_data
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

        if event_data.get(ATTR_INDICATIONS_DICT) is None and event_data[ATTR_INDICATIONS]:
            event_data[ATTR_INDICATIONS_DICT] = {
                "t%d" % i: v for i, v in enumerate(event_data[ATTR_INDICATIONS], start=1)
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
        meter_zones = self._entity_data.zones

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

        meter = self._entity_data

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

            if not event_data.get(ATTR_SUCCESS):
                raise Exception(event_data[ATTR_COMMENT] or "comment not provided")

    async def async_calculate_indications(self, **call_data):
        meter = self._entity_data

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

        if not event_data.get(ATTR_SUCCESS):
            raise Exception(event_data[ATTR_COMMENT] or "comment not provided")

    @classmethod
    async def async_refresh_accounts(
        cls: Type[_TMESEntity],
        entities: Dict[Hashable, Optional[_TMESEntity]],
        account: "Account",
        config_entry: ConfigEntry,
        final_config: ConfigType,
    ) -> Optional[Iterable[_TMESEntity]]:
        if isinstance(account, AbstractAccountWithMeters):
            meters = await account.async_get_meters()

            for meter_id, meter in meters.items():
                entity_key = (account.id, meter_id)
                try:
                    entity = entities[entity_key]
                except KeyError:
                    entity = cls(
                        final_config[CONF_NAME_FORMAT][cls.config_key][meter.code],
                        timedelta(hours=1),
                        account,
                        meter,
                    )
                    entities[entity_key] = entity
                    return [entity]
                else:
                    if entity.enabled:
                        entity.async_schedule_update_ha_state(force_refresh=True)

    async def async_update(self) -> None:
        meters = await self._account.async_get_meters()
        meter_data = meters.get(self._entity_data.id)
        if meter_data is not None:
            self._entity_data = meter_data


class MESInvoiceSensor(MESEntity[AbstractAccountWithInvoices, AbstractInvoice]):
    config_key = CONF_INVOICES

    @property
    def device_class(self) -> Optional[str]:
        return DOMAIN + "_invoices"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor"""
        acc = self._account
        return f"{acc.api.__class__.__name__}_invoice_{acc.id}"

    @property
    def state(self) -> Union[float, str]:
        invoice = self._entity_data
        return round(invoice.total or 0.0, 2) if invoice else STATE_UNAVAILABLE

    @property
    def icon(self) -> str:
        return "mdi:receipt"

    @property
    def unit_of_measurement(self) -> str:
        return "руб." if self._entity_data else None

    @property
    def sensor_related_attributes(self):
        invoice = self._entity_data

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
        invoice = self._entity_data
        return {
            "type": "invoice",
            "period": invoice.period.isoformat(),
            "id": invoice.id,
            "account_code": self._account.code,
        }

    @classmethod
    async def async_refresh_accounts(
        cls: Type[_TMESEntity],
        entities: Dict[Hashable, _TMESEntity],
        account: "Account",
        config_entry: ConfigEntry,
        final_config: ConfigType,
    ) -> Optional[Iterable[_TMESEntity]]:
        entity_key = account.id

        if isinstance(account, AbstractAccountWithInvoices):
            try:
                entity = entities[entity_key]
            except KeyError:
                entity = cls(
                    final_config[CONF_NAME_FORMAT][cls.config_key][account.code],
                    timedelta(hours=1),
                    account,
                )
                entities[entity_key] = entity
                return [entity]
            else:
                if entity.enabled:
                    await entity.async_update_ha_state(force_refresh=True)

        return None

    async def async_update(self) -> None:
        self._entity_data = await self._account.async_get_last_invoice()


async_setup_entry = make_common_async_setup_entry(
    MESAccountSensor, MESInvoiceSensor, MESMeterSensor
)
