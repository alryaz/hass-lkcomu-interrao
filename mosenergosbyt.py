from urllib import parse, request
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import json


class MESAPI():

    def __init__(self, username, password, useCache=True):
        self._username = username
        self._password = password
        self._userAgent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            'AppleWebKit/537.36 (KHTML, like Gecko)'
            'Chrome/76.0.3809.100 Safari/537.36'
        )

        self._empty_vars()

        self._login()

    def _empty_vars(self):
        self._session = None
        self._id_profile = None
        self._token = None
        self._accounts = None

    def _lk_request(self, action, query, postFields, method='POST',
                    getFields={}):
        data = parse.urlencode(postFields).encode()
        getFields['action'] = action
        getFields['query'] = query
        if self._session is not None:
            getFields['session'] = self._session

        req = request.Request(
            ("https://my.mosenergosbyt.ru/gate_lkcomu?" +
             parse.urlencode(getFields)),
            data=data
        )
        response = request.urlopen(req)

        data = json.loads(response.read().decode('utf-8'))

        if data['success'] is not None and data['success']:
            return data
        elif data['err_code'] == 201:
            self._login()
            return self._lk_request(
                action, query, postFields,
                method, getFields
            )
        else:
            raise OSError('asdf')

    def _lk_sql(self, query, postFields=[]):
        return self._lk_request('sql', query, postFields, 'POST')

    def _get_cookies(self):
        return ';'.join(self._cookieJar)

    def _session_init(self):
        self._cookieJar = []

        req = request.Request("https://my.mosenergosbyt.ru/auth")
        response = request.urlopen(req)
        cookie = response.headers.get('Set-Cookie')

        sessionCookie = cookie.split(';')[0]

        self._cookieJar.append(sessionCookie)

    def _login(self):
        self._session_init()

        data = self._lk_request('auth', 'login', {
            'login': self._username,
            'psw': self._password,
            'remember': True,
            'vl_device_info': json.dumps({
                'appver': '1.8.0',
                'type': 'browser',
                'userAgent': self._userAgent
            })
        })

        # @TODO: Multiple profiles possible?
        profile = data['data'][0]
        if profile['id_profile'] is None:
            raise Exception(profile['nm_result'])

        self._id_profile = profile['id_profile']
        self._session = profile['session']
        self._token = profile['new_token']

        self._lk_sql('Init')
        self._lk_sql('NoticeRoutine')

        return True

    def _logout(self):
        # @TODO: make a real logout feature
        self._empty_vars()

        return True

    # API METHODS BEGIN
    def GetAccounts(self, idList=[]):
        if self._accounts is None:
            response = self._lk_sql('LSList')

            self._accounts = {
                account['nn_ls']: MESAccount(
                    account_data=account,
                    api_object=self
                )
                for account in response['data']
                if account['kd_service_type'] == 1
            }

        if idList:
            return {k: v for k, v in self._accounts.items() if k in idList}

        return self._accounts

    def GetAccountsList(self, idList=[]):
        return list(self.GetAccounts(idList).values())


class MESAccount():

    def __init__(self, account_data, api_object):
        self._account_data = account_data
        self._api_object = api_object

    def _retrieve_account_info(self):
        # @TODO: implement this
        raise Exception('[NOT IMPLEMENTED]')

    def _lk_bytProxy(self, proxyQuery, data={}):
        data['vl_provider'] = self._account_data['vl_provider']
        data['proxyquery'] = proxyQuery
        data['plugin'] = 'bytProxy'
        return self._api_object._lk_request(
            action='sql',
            query='bytProxy',
            postFields=data
        )

    def GetMeters(self, idList=[]):
        response = self._lk_bytProxy('Meters')

        return {
            meter['nm_meter_num']: MESMeter(
                meter_data=meter,
                api_object=self._api_object,
                account_object=self
            )
            for meter in response['data']
            if not idList or meter['nm_meter_num'] in idList
        }

    def GetMetersList(self, idList=[]):
        return list(self.GetMeters(idList).values())

    def GetNumber(self):
        return self._account_data['nn_ls']

    def GetAddress(self):
        return self._account_data['data']['nm_street']

    def GetPayments(self, periodStart, periodEnd):
        response = self._lk_bytProxy('Pays', {
            'dt_st': periodStart.isoformat(),
            'dt_en': periodEnd.isoformat()
        })
        payments = []
        for payment in response['data']:
            payments.append({
                'date': datetime.fromisoformat(payment['dt_pay']),
                'amount': payment['sm_pay'],
                'status': payment['nm_status'],
            })
        return payments

    def GetLatestPayments(self, latestMonths=3):
        now = datetime.now()
        return self.GetPayments(now - relativedelta(months=latestMonths), now)

    def GetLastPayment(self):
        return self.GetLatestPayments()[0]

    def GetCurrentBalance(self):
        response = self._lk_bytProxy('CurrentBalance')
        return response['data'][0]['vl_balance']

    def GetRemainingDaysToSendIndications(self):
        response = self._lk_bytProxy('IndicationCounter')
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

    def GetServiceID(self):
        return self._account_data['id_service']

    def GetAccountURL(self):
        return ('https://my.mosenergosbyt.ru/accounts/' +
                self._account_data['id_service'])


class MESMeter():

    def __init__(self, meter_data, api_object, account_object):
        self._meter_data = meter_data
        self._api_object = api_object
        self._account_object = account_object

        self._meter_tariff_count = None

    def GetNumber(self):
        return self._meter_data['nm_meter_num']

    def GetInstallDate(self):
        return self._meter_data['dt_meter_install']

    def GetDeviceModel(self):
        return self._meter_data['nm_mrk']

    def GetTariffCount(self):
        if self._meter_tariff_count is not None:
            self._meter_tariff_count = len([
                k for k in self._meter_data.keys() if k[:1] == 'nm_t'
            ])
        return self._meter_tariff_count

    def GetSubmittedIndications(self):
        return {
            k[3:5]: v
            for k, v in self._meter_data.items()
            if k[:4] == 'vl_t' and k[-6:] == '_today'
        }

    def GetLastIndications(self):
        return {
            k[3:5]: v
            for k, v in self._meter_data.items()
            if k[:4] == 'vl_t' and k[-9:] == '_last_ind'
        }

    def GetPeriodStartDate(self):
        today = date.today()
        return date(
            today.year, today.month,
            self._meter_data['nn_period_start']
        )

    def GetPeriodEndDate(self):
        today = date.today()
        return date(
            today.year, today.month,
            self._meter_data['nn_period_end']
        )

    def GetRemainingDaysToSendIndications(self):
        return (self.GetPeriodEndDate() - date.today()).days + 1

    def GetCurrentStatus(self):
        return self._meter_data['nm_result']
