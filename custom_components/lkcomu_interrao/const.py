"""Constants for lkcomu_interrao integration"""

DOMAIN = "lkcomu_interrao"

ATTRIBUTION_RU = "Данные получены с %s"
ATTRIBUTION_EN = "Data acquired from %s"

ATTR_ACCOUNT_CODE = "account_code"
ATTR_ADDRESS = "address"
ATTR_BENEFITS = "benefits"
ATTR_CALL_PARAMS = "call_params"
ATTR_CHARGED = "charged"
ATTR_COMMENT = "comment"
ATTR_CORRECT = "correct"
ATTR_COST = "cost"
ATTR_DESCRIPTION = "description"
ATTR_FMT_LAST_VALUE = "last_value_%s"
ATTR_FMT_SUBMITTED_VALUE = "submitted_value_%s"
ATTR_FMT_TODAY_VALUE = "today_value_%s"
ATTR_IGNORE_INDICATIONS = "ignore_indications"
ATTR_IGNORE_PERIOD = "ignore_period"
ATTR_INCREMENTAL = "incremental"
ATTR_INDICATIONS = "indications"
ATTR_INITIAL = "initial"
ATTR_INSTALL_DATE = "install_date"
ATTR_INSURANCE = "insurance"
ATTR_INVOICE_ID = "invoice_id"
ATTR_LAST_PAYMENT_AMOUNT = "last_payment_amount"
ATTR_LAST_PAYMENT_DATE = "last_payment_date"
ATTR_LAST_PAYMENT_STATUS = "last_payment_status"
ATTR_LAST_SUBMIT_DATE = "last_submit_date"
ATTR_METER_CODE = "meter_code"
ATTR_MODEL = "model"
ATTR_NOTIFICATION = "notification"
ATTR_PAID = "paid"
ATTR_PENALTY = "penalty"
ATTR_PERIOD = "period"
ATTR_PROVIDER_NAME = "provider_name"
ATTR_REASON = "reason"
ATTR_REMAINING_DAYS = "remaining_days"
ATTR_SERVICE_NAME = "service_name"
ATTR_SERVICE_TYPE = "service_type"
ATTR_STATUS = "status"
ATTR_SUBMIT_PERIOD_ACTIVE = "submit_period_active"
ATTR_SUBMIT_PERIOD_END = "submit_period_end"
ATTR_SUBMIT_PERIOD_START = "submit_period_start"
ATTR_SUCCESS = "success"
ATTR_TOTAL = "total"
ATTR_UNIT = "unit"
ATTR_PROVIDER_TYPE = "provider_type"

CONF_ACCOUNTS = "accounts"
CONF_INVOICES = "invoices"
CONF_METERS = "meters"
CONF_NAME_FORMAT = "name_format"
CONF_USER_AGENT = "user_agent"
CONF_PAYMENTS = "payments"
CONF_DEV_PRESENTATION = "dev_presentation"

DATA_API_OBJECTS = DOMAIN + "_api_objects"
DATA_ENTITIES = DOMAIN + "_entities"
DATA_FINAL_CONFIG = DOMAIN + "_final_config"
DATA_UPDATE_LISTENERS = DOMAIN + "_update_listeners"
DATA_YAML_CONFIG = DOMAIN + "_yaml_config"
DATA_UPDATE_DELEGATORS = DOMAIN + "_update_delegators"

DEFAULT_NAME_FORMAT_EN_ACCOUNTS = "{provider_code_upper} {account_code} {type_en_cap}"
DEFAULT_NAME_FORMAT_EN_INVOICES = "{provider_code_upper} {account_code} {type_en_cap}"
DEFAULT_NAME_FORMAT_EN_METERS = "{provider_code_upper} {account_code} {type_en_cap} {code}"
DEFAULT_NAME_FORMAT_EN_PAYMENTS = "{provider_code_upper} {account_code} {type_en_cap}"

DEFAULT_NAME_FORMAT_RU_ACCOUNTS = "{provider_code_upper} {account_code} {type_ru_cap}"
DEFAULT_NAME_FORMAT_RU_INVOICES = "{provider_code_upper} {account_code} {type_ru_cap}"
DEFAULT_NAME_FORMAT_RU_METERS = "{provider_code_upper} {account_code} {type_ru_cap} {code}"
DEFAULT_NAME_FORMAT_RU_PAYMRUTS = "{provider_code_upper} {account_code} {type_ru_cap}"

DEFAULT_MAX_INDICATIONS = 3
DEFAULT_SCAN_INTERVAL = 60 * 60  # 1 hour

API_TYPE_DEFAULT = "moscow"
API_TYPE_NAMES = {
    "altai": "Алтайэнергосбыт",
    "bashkortostan": "Башэлектросбыт (ЭСКБ)",
    "moscow": "Мосэнерго / МосОблЕИРЦ / ПАО ",
    "oryol": "Орловский Энергосбыт / ЕПД",
    "saratov": "Саратовский Энергосбыт",
    "sevesk": "Северная Сбытовая Компания (ССК)",
    "tambov": "Тамбовский Энергосбыт",
    "tomsk": "Томский Энергосбыт / РТС",
    "volga": "Энергосбыт «Волга»",
}


SUPPORTED_PLATFORMS = ("sensor", "binary_sensor")
ATTR_AMOUNT = "amount"
ATTR_AGENT = "agent"
ATTR_GROUP = "group"
ATTR_PAID_AT = "paid_at"
FORMAT_VAR_TYPE_RU = "type_ru"
FORMAT_VAR_TYPE_EN = "type_en"
FORMAT_VAR_CODE = "code"
FORMAT_VAR_ID = "id"
FORMAT_VAR_ACCOUNT_ID = "account_id"
FORMAT_VAR_ACCOUNT_CODE = "account_code"
FORMAT_VAR_PROVIDER_CODE = "provider_code"
FORMAT_VAR_PROVIDER_NAME = "provider_name"
ATTR_FULL_NAME = "full_name"
ATTR_LIVING_AREA = "living_area"
ATTR_TOTAL_AREA = "total_area"
