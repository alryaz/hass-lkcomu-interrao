_ЕЛК ЖКХ &#xab;Интер РАО&#xbb; для Home Assistant_
=======

## Введение
> @ TODO @

## Установка
### Посредством HACS
> **✔️️ Рекомендуемый метод**
1. Установите HACS

> @ TODO @

### Вручную
> **⚠️ Не рекомендуется**

## Конфигурация
> @ TODO @
### Посредством YAML
> @ TODO @
#### Для одной учётной записи
```yaml
# Файл configuration.yaml
...

lkcomu_interrao:
  username: username1
  password: password1
```

#### Для нескольких учётных записей
```yaml
# Файл configuration.yaml
...

lkcomu_interrao:
  # По умолчанию используется ЕЛК Мосэнергосбыт
  - username: username1
    password: password1

  # Чтобы использовать другой ЕЛК, задайте значение параметру `type`
  - type: altai
    username: username2
    password: password2

  # Использование одного и того же имени пользователя возможно
  # для разных типов поставщиков.
  - type: volga
    username: username2
    password: password2
```

## Поддерживаемые ЛК

Ниже предъявлен перечень поддерживаемых ЛК с их внутренними идентификаторами.
Данные идентификаторы используются как значение для поля `type`.

> **Внимание:** Поддерживаются только ЛК физ. лиц. Поддержка ЛК юридических лиц не планируется.

### Алтайэнергосбыт &mdash; `altai`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/altai.png" height="50" alt="ЕЛК ЖКХ ССК">](https://lkfl.altaiensb.com)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков
- Отображение последних квитанций
- Отображение последних платежей
- Передача показаний по счётчикам

### Башэлектросбыт &mdash; `bashkortostan`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/bashkortostan.png" height="50" alt="ЕЛК ЖКХ ССК">](https://lkk.bashesk.ru/)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков
- Отображение последних квитанций
- Отображение последних платежей
- Передача показаний по счётчикам

### Мосэнергосбыт &mdash; `moscow`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/moscow.png" height="50" alt="ЕЛК ЖКХ ССК">](https://my.mosenergosbyt.ru/)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков<sup>1</sup>
- Отображение последних квитанций
- Отображение последних платежей
- Передача показаний по счётчикам<sup>2</sup>

_<sup>1</sup> Для поставщика ТКО может применяться виртуализация счётчика_<br>
_<sup>2</sup> На данный момент только для Мосэнергосбыт и МосОблЕИРЦ_  

### Орловский Энергосбыт &mdash; `oryol`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/oryol.png" height="50" alt="ЕЛК ЖКХ ССК" >](https://my.interrao-orel.ru/)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков
- Отображение последних квитанций
- Отображение последних платежей
- Передача показаний по счётчикам

### Саратовэнерго &mdash; `saratov`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/saratov.png" height="50" alt="ЕЛК ЖКХ ССК">](https://my.saratovenergo.ru/)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков
- Отображение последних квитанций
- Отображение последних платежей
- Передача показаний по счётчикам


### Северная Сбытовая Компания (ССК) &mdash; `sevesk`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/sevesk.png" height="50" alt="ЕЛК ЖКХ ССК">](https://lk.sevesk.ru/)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков
- Отображение последних квитанций
- Отображение последних платежей
- Передача показаний по счётчикам


### Тамбовская Энергосбытовая Компания (ТЭСК) &mdash; `tambov`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/tambov.png" height="50" alt="ЕЛК ЖКХ ССК">](https://my.tesk.su/)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков
- Отображение последних квитанций
- Отображение последних платежей
- Передача показаний по счётчикам

### Томскэнергосбыт &mdash; `tomsk`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/tomsk.png" height="50" alt="ЕЛК ЖКХ ССК">](https://my.tomskenergosbyt.ru/)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков<sup>1</sup>
- Отображение последних квитанций
- Отображение последних платежей<sup>1</sup>
- Передача показаний по счётчикам<sup>1</sup>

_<sup>1</sup> На данный момент только АО "Томскэнергосбыт"_

### Энергосбыт Волга - `volga`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/volga.png" height="50" alt="ЕЛК ЖКХ ССК">](https://my.esbvolga.ru/)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков
- Отображение последних квитанций
- Отображение последних платежей
- Передача показаний по счётчикам

## Дополнительная информация
> @ TODO @