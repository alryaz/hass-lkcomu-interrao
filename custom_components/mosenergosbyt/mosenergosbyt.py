""" Basic Mosenergosbyt API interaction. """
import asyncio
from typing import Optional, List, Dict
from urllib import parse, request
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import aiohttp
import json
import logging

_LOGGER = logging.getLogger(__name__)


class API:

    AUTH_URL = "https://my.mosenergosbyt.ru/auth"
    REQUEST_URL = "https://my.mosenergosbyt.ru/gate_lkcomu"
    ACCOUNT_URL = "https://my.mosenergosbyt.ru/accounts/"

    def __init__(self, username: str, password: str, cache: bool = True, timeout: int = 5):
        self.__username = username
        self.__password = password

        self._user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            'AppleWebKit/537.36 (KHTML, like Gecko)'
            'Chrome/76.0.3809.100 Safari/537.36'
        )

        self._session: Optional[aiohttp.ClientSession] = None
        self._session_id: Optional[str] = None
        self._id_profile = None
        self._token = None
        self._accounts = None
        self._cookie_jar = None
        self._logged_in_at = None

        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def request(self, action, query, post_fields: Optional[Dict] = None, method='POST',
                      get_fields: Optional[Dict] = None, fail_on_reauth: bool = False):
        data = parse.urlencode(post_fields).encode() if post_fields else None

        if get_fields is None:
            get_fields = {}

        get_fields['action'] = action
        get_fields['query'] = query
        if self._session_id is not None:
            get_fields['session'] = self._session_id

        request_url = self.REQUEST_URL + '?' + parse.urlencode(get_fields)
        response_text = None
        try:
            async with self._session.post(request_url, data=post_fields) as response:
                response_text = await response.text(encoding='utf-8')
                data = json.loads(response_text)

        except asyncio.exceptions.TimeoutError as e:
            raise MosenergosbytException('Timeout error (interaction exceeded %d seconds)'
                                         % self._timeout.total) from None

        except OSError as e:
            raise MosenergosbytException('Request error') from e

        except json.JSONDecodeError as e:
            _LOGGER.debug('Response contents: %s' % response_text)
            raise MosenergosbytException('Response contains invalid JSON') from None

        if data['success'] is not None and data['success']:
            return data
        elif data['err_code'] == 201:
            if fail_on_reauth:
                raise MosenergosbytException('Request returned')
            await self.login()
            return await self.request(
                action, query, post_fields,
                method, get_fields,
                fail_on_reauth=True
            )
        else:
            raise MosenergosbytException('Unknown error')

    async def request_sql(self, query, post_fields: Optional[Dict] = None):
        return await self.request('sql', query, post_fields, 'POST')

    def _get_cookies(self):
        return ';'.join(self._cookie_jar)

    async def login(self):
        self._session = aiohttp.ClientSession(raise_for_status=True, timeout=self._timeout)

        # await self._session.get(self.AUTH_URL)

        data = await self.request('auth', 'login', {
            'login': self.__username,
            'psw': self.__password,
            'remember': True,
            'vl_device_info': json.dumps({
                'appver': '1.8.0',
                'type': 'browser',
                'userAgent': self._user_agent
            })
        })

        # @TODO: Multiple profiles possible?
        profile = data['data'][0]
        if profile['id_profile'] is None:
            raise MosenergosbytException(profile['nm_result'])

        self._id_profile = profile['id_profile']
        self._session_id = profile['session']
        self._token = profile['new_token']

        await self.request_sql('Init')
        await self.request_sql('NoticeRoutine')

        self._logged_in_at = datetime.utcnow()

        return True

    @property
    def logged_in_at(self) -> datetime:
        return self._logged_in_at

    async def logout(self):
        if self._session:
            await self._session.close()
        # @TODO: make a real logout feature
        self._session = None
        self._id_profile = None
        self._token = None
        self._accounts = None
        self._cookie_jar = None
        self._logged_in_at = None

        return True

    # API METHODS BEGIN
    async def get_accounts(self) -> Dict[str, 'Account']:
        if self._accounts is None:
            response = await self.request_sql('LSList')

            self._accounts = {
                account['nn_ls']: Account(
                    account_data=account,
                    api=self
                )
                for account in response['data']
                if account['kd_service_type'] == 1
            }

        return self._accounts

    async def get_accounts_list(self):
        accounts = await self.get_accounts()
        return list(accounts.values())


class Account:

    def __init__(self, account_data, api):
        self._account_data = account_data
        self.api = api

    def _retrieve_account_info(self):
        # @TODO: implement this
        raise MosenergosbytException('[NOT IMPLEMENTED]')

    async def _lk_byt_proxy(self, proxy_query, data: Optional[Dict] = None):
        data = {} if data is None else {**data}
        data['vl_provider'] = self._account_data['vl_provider']
        data['proxyquery'] = proxy_query
        data['plugin'] = 'bytProxy'
        return await self.api.request(
            action='sql',
            query='bytProxy',
            post_fields=data
        )

    async def get_meters(self):
        response = await self._lk_byt_proxy('Meters')

        return {
            meter['nm_meter_num']: Meter(api=self.api, account=self, data=meter)
            for meter in response['data']
        }

    @property
    def account_code(self):
        return self._account_data['nn_ls']

    @property
    def address(self):
        return self._account_data['data']['nm_street']

    async def get_payments(self, start: datetime, end: datetime) -> List[Dict]:
        response = await self._lk_byt_proxy('Pays', {
            'dt_st': start.isoformat(),
            'dt_en': end.isoformat()
        })
        payments = []
        for payment in response['data']:
            payments.append({
                'date': datetime.fromisoformat(payment['dt_pay']),
                'amount': payment['sm_pay'],
                'status': payment['nm_status'],
            })
        return payments

    async def get_latest_payments(self, months: int = 3) -> List[Dict]:
        now = datetime.now()
        return await self.get_payments(now - relativedelta(months=months), now)

    async def get_last_payment(self) -> Optional[Dict]:
        payments = await self.get_latest_payments()
        if not payments:
            return None
        return payments[0]

    async def get_current_balance(self):
        response = await self._lk_byt_proxy('CurrentBalance')
        return response['data'][0]['vl_balance']

    async def get_remaining_days(self):
        response = await self._lk_byt_proxy('IndicationCounter')
        days = response['data'][0]['nn_days']
        if days > 0:
            return days
        else:
            return 0

#    def GetIndications(self, periodStart, periodEnd):
#        response = self._lk_bytProxy('Indications', {
#            'dt_st': periodStart.isoformat(),
#            'dt_en': periodEnd.isoformat()
#        })
#        return [{
#            'date': indication['dt_indication'],
#            'by': indication['nm_take'],
#            'source': indication['nm_indication_take'],
#            'meters': {
#                k[-2:]: v
#                for k, v in indication.items()
#                if k[:-1] == 'vl_t'
#            }
#        } for indication in response['data']]
#
#    def GetLatestIndications(self, latestMonths=3):
#        now = datetime.now()
#        return self.GetIndications(
#            now - relativedelta(months=latestMonths),
#            now
#        )
#
#    def GetLastIndications(self):
#        return self.GetLatestIndications()[0]

    @property
    def service_id(self):
        return self._account_data['id_service']

    @property
    def account_url(self):
        return self.ACCOUNT_URL + self._account_data['id_service']


class Meter:

    def __init__(self, api: 'API', account: 'Account', data: Optional[Dict] = None):
        if data is None:
            data = {}

        self._data = data
        self._api = api
        self._account = account

        self._meter_tariff_count = None

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value: Optional[Dict]):
        if value != self._data:
            self._meter_tariff_count = None
        self._data = value

    @property
    def meter_id(self) -> Optional[str]:
        return self._data.get('nm_meter_num')

    @property
    def account_code(self) -> str:
        return self._account.account_code

    @property
    def install_date(self) -> Optional[str]:
        return self._data.get('dt_meter_install')

    @property
    def model(self) -> Optional[str]:
        return self._data.get('nm_mrk')

    @property
    def tariff_count(self) -> int:
        if self._data is None:
            return 0
        if self._meter_tariff_count is not None:
            self._meter_tariff_count = len([
                k for k in self._data.keys() if k[:1] == 'nm_t'
            ])
        return self._meter_tariff_count

    @property
    def submitted_indications(self):
        if self._data is None:
            return {}
        return {
            k[3:5]: v
            for k, v in self._data.items()
            if k[:4] == 'vl_t' and k[-6:] == '_today'
        }

    @property
    def last_indications(self):
        return {
            k[3:5]: v
            for k, v in self._data.items()
            if k[:4] == 'vl_t' and k[-9:] == '_last_ind'
        }

    @property
    def period_start_date(self):
        today = date.today()
        return date(
            today.year, today.month,
            self._data.get('nn_period_start')
        )

    @property
    def period_end_date(self):
        today = date.today()
        return date(
            today.year, today.month,
            self._data.get('nn_period_end')
        )

    @property
    def remaining_days(self):
        return (self.period_end_date - date.today()).days + 1

    @property
    def current_status(self):
        return self._data.get('nm_result')


class MosenergosbytException(Exception):
    pass
