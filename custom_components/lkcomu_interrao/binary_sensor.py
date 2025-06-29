from typing import (
    Any,
    ClassVar,
    Hashable,
    Iterable,
    Mapping,
    TypeVar,
)

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import slugify

from custom_components.lkcomu_interrao._base import (
    LkcomuInterRAOEntity,
    make_common_async_setup_entry,
)
from custom_components.lkcomu_interrao._encoders import payment_to_attrs
from custom_components.lkcomu_interrao.const import CONF_LAST_PAYMENT

from inter_rao_energosbyt.interfaces import (
    AbstractAccountWithPayments,
    AbstractPayment,
    Account,
)

_TLkcomuInterRAOEntity = TypeVar("_TLkcomuInterRAOEntity", bound=LkcomuInterRAOEntity)


class LkcomuInterRAOLastPayment(
    LkcomuInterRAOEntity[AbstractAccountWithPayments], BinarySensorEntity
):
    _attr_icon = "mdi:cash-multiple"

    config_key: ClassVar[str] = CONF_LAST_PAYMENT

    def __init__(
        self, *args, last_payment: AbstractPayment | None = None, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self._last_payment = last_payment

        self._entity_id: str | None = f"binary_sensor." + slugify(
            f"{self.account_provider_code or 'unknown'}_{self._account.code}_last_payment"
        )

    @property
    def is_on(self) -> bool | None:
        payment = self._last_payment
        if payment is None:
            return None
        return payment.is_accepted

    @property
    def entity_id(self) -> str | None:
        return self._entity_id

    @entity_id.setter
    def entity_id(self, value: str | None) -> None:
        self._entity_id = value

    #################################################################################
    # Implementation base of inherent class
    #################################################################################

    @classmethod
    async def async_refresh_accounts(
        cls: type[_TLkcomuInterRAOEntity],
        entities: dict[Hashable, _TLkcomuInterRAOEntity],
        account: "Account",
        config_entry: ConfigEntry,
        account_config: ConfigType,
    ) -> Iterable[_TLkcomuInterRAOEntity] | None:
        if isinstance(account, AbstractAccountWithPayments):
            entity_key = account.id

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

    async def async_update_internal(self) -> None:
        self._last_payment = await self._account.async_get_last_payment()

    #################################################################################
    # Data-oriented implementation of inherent class
    #################################################################################

    @property
    def sensor_related_attributes(self) -> Mapping[str, Any] | None:
        payment = self._last_payment
        if payment:
            return payment_to_attrs(payment)

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor"""
        acc = self._account
        return f"{acc.api.__class__.__name__}_lastpayment_{acc.id}"


async_setup_entry = make_common_async_setup_entry(LkcomuInterRAOLastPayment)
