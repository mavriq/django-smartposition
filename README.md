====================
django-smartposition
====================

Номер позиции в списке "parent_field"-а
При удалении записи, или изменении позиции - номера позиций остальных записей изменяются соответствующим образом


usage:
class RecordLists(Model):
    owner = ForeignKey(to='Users')
    position = SmartPositionField(parent_field='owner')
    record = ...

Далее, при добавлении, или изменении позиции одной записи owner-а - соответствующим образом изменятся другиие номера позиций этого owner-а


Если parent_field не указан - то нумерация идет по всей таблице

