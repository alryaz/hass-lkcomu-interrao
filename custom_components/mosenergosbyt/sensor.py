"""
Sensor for Mosenergosbyt cabinet.
Retrieves values regarding current state of accounts.
"""
import logging
from datetime import timedelta
from homeassistant.helpers.entity import Entity
from .mosenergosbyt import MESAPI, MESAccount

__version__ = '0.0.1'

_LOGGER = logging.getLogger(__name__)

# DEFAULT_PICTURE_ICON = 'data:image/png;base64,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'

async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the sensor platform"""

    try:
        if discovery_info is None:
            _LOGGER.wraning('No accounts loaded, check your configuration')
            return False

        entities = []
        account_count = 0
        meter_count = 0
        for account_object in discovery_info:
            entities.append(MESAccountSensor(account_object))
            account_count += 1

            for meter_object in account_object.GetMetersList():
                entities.append(MESMeterSensor(meter_object))
                meter_count += 1
        async_add_entities(entities, update_before_add=True)
        if account_count+meter_count > 0:
            _LOGGER.info('Discovered ' +
                         str(account_count+meter_count) +
                         ' accounts/meters')

            return True
        else:
            _LOGGER.warning('No accounts discovered, check your configuration')
            return False
    except Exception as e:
        _LOGGER.critical('Cant setup mosenergosbyt logging: ' + str(e))
        return False


class MESAccountSensor(Entity):
    """The class for this sensor"""
    def __init__(self, account):
        self._account = account

    async def async_update(self):
        """The update method"""
        last_payment = self._account.GetLastPayment()

        attributes = {
            'Number': self._account.GetNumber(),
            'CurrentBalance': self._account.GetCurrentBalance(),
            'Address': self._account.GetAddress(),
            'LastPaymentDate': last_payment['date'],
            'LastPaymentAmount': last_payment['amount'],
            'LastPaymentStatus': last_payment['status'],
            'RemainingDaysToSendIndications':
            self._account.GetRemainingDaysToSendIndications(),
        }

        self._state = (
            '+' if attributes['CurrentBalance'] > 0
            else '-' if attributes['CurrentBalance'] < 0
            else ''
        ) + str(attributes['CurrentBalance'])
        self._unit = 'руб.'
        self._attributes = attributes

    @property
    def name(self):
        """Return the name of the sensor"""
        return 'MES Account ' + self._account.GetNumber()

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
        return 'ls_' + str(self._account.GetServiceID())


class MESMeterSensor(Entity):
    """The class for this sensor"""
    def __init__(self, meter):
        self._meter = meter
        self._entity_picture = None

    async def async_update(self):
        """The update method"""
        attributes = {
            'Number': self._meter.GetNumber(),
            'InstallDate': self._meter.GetInstallDate(),
            'RemainingDaysToSendIndications':
            self._meter.GetRemainingDaysToSendIndications(),
        }
        for tariff, value in self._meter.GetSubmittedIndications().items():
            attributes['SubmittedIndicationValue' + tariff.upper()] = value
        for tariff, value in self._meter.GetLastIndications().items():
            attributes['LastIndicationValue' + tariff.upper()] = value

        self._state = self._meter.GetCurrentStatus()
        self._attributes = attributes

    @property
    def name(self):
        """Return the name of the sensor"""
        return 'MES Meter ' + self._meter.GetNumber()

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
        return 'meter_' + str(self._meter.GetNumber())
