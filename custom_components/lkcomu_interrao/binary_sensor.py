from datetime import timedelta
from typing import Any, Dict, Hashable, Iterable, Mapping, Optional, Type, TypeVar

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.helpers.typing import HomeAssistantType, StateType, ConfigType

from custom_components.lkcomu_interrao._base import MESEntity, make_common_async_setup_entry
from custom_components.lkcomu_interrao.const import CONF_PAYMENTS, DOMAIN
from inter_rao_energosbyt.interfaces import AbstractAccountWithPayments, AbstractPayment, Account


_TMESEntity = TypeVar("_TMESEntity", bound="MESEntity")


class MESLastPaymentSensor(
    MESEntity[AbstractAccountWithPayments, AbstractPayment],
    BinarySensorEntity,
):
    config_key = CONF_PAYMENTS

    @property
    def is_on(self) -> bool:
        payment = self._entity_data
        return payment is not None and payment.is_accepted

    #################################################################################
    # Implementation base of inherent class
    #################################################################################

    @classmethod
    async def async_refresh_accounts(
        cls: Type[_TMESEntity],
        entities: Dict[Hashable, _TMESEntity],
        account: "Account",
        config_entry: ConfigEntry,
        final_config: ConfigType,
    ) -> Optional[Iterable[_TMESEntity]]:
        entity_key = account.id

        if isinstance(account, AbstractAccountWithPayments):
            try:
                entity = entities[entity_key]
            except KeyError:
                entity = cls(f"{account.id} Payment", timedelta(hours=1), account)
                entities[entity_key] = entity
                return [entity]
            else:
                if entity.enabled:
                    await entity.async_update_ha_state(force_refresh=True)

        return None

    async def async_update(self) -> None:
        self._entity_data = await self._account.async_get_last_payment()

    #################################################################################
    # Data-oriented implementation of inherent class
    #################################################################################

    @property
    def state(self) -> StateType:
        data = self._entity_data
        if data is None:
            return STATE_UNAVAILABLE
        return STATE_ON if self.is_on else STATE_OFF

    @property
    def icon(self) -> str:
        return "mdi:cash-multiple"

    @property
    def sensor_related_attributes(self) -> Optional[Mapping[str, Any]]:
        payment = self._entity_data

        attributes = (
            {}
            if payment is None
            else {
                "status": payment.status,
                "amount": payment.amount,
                "agent": payment.agent,
            }
        )

        attributes["account_id"] = self._account.id

        return attributes

    @property
    def name_format_values(self) -> Mapping[str, Any]:
        return {
            "type_en": "payment",
            "cap_type_en": "Payment",
            "type_ru": "платёж",
            "cap_type_ru": "Платёж",
        }

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor"""
        acc = self._account
        return f"{acc.api.__class__.__name__}_payment_{acc.id}"

    @property
    def device_class(self) -> Optional[str]:
        return DOMAIN + "_payment"


async_setup_entry = make_common_async_setup_entry(MESLastPaymentSensor)
