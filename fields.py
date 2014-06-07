# -*- coding: utf-8 -*-
__author__ = 'mavriq'
__all__ = ['SmartPositionField', ]


from django.db.models.fields import PositiveIntegerField
from django.db.models import F, signals


class SmartPositionField(PositiveIntegerField):
    """
    Номер позиции в списке "parent_field"-а
    usage:
    class RecordLists(Model):
        owner = ForeignKey(to='Users')
        position = SmartPositionField(parent_field='owner')
        record = ...
    Далее здесь при добавлении, или изменении позиции одной записи owner-а - соответствующим образом изменятся другиие
    ... номера позиций этого owner-а
    """
    def contribute_to_class(self, cls, name, **kwargs):
        super(SmartPositionField, self).contribute_to_class(cls, name, **kwargs)
        signals.pre_save.connect(self._pre_save_position, sender=cls)
        signals.post_delete.connect(self._post_delete_position, sender=cls)
        # signals.post_save.connect(self._pos_post_save, sender=cls)

    def __init__(self, parent_field='', *args, **kwargs):
        for arg in ('primary', 'unique', 'default'):
            if kwargs.get(arg, False):
                raise TypeError("argument '%s' can't be specified to %s." % (arg, self.__class__))
        kwargs['default'] = 0
        # self.parent_field = kwargs.pop('parent_field', '')
        self.parent_field = parent_field
        super(SmartPositionField, self).__init__(*args, **kwargs)

    def _pre_save_position(self, instance, *args, **kwargs):
        position, parent, model = \
            getattr(instance, self.attname), \
            getattr(instance, self.parent_field, None), \
            instance.__class__
        if parent:
            manager = model.objects.select_for_update().filter(**{self.parent_field: parent})
            # сначала лочим, потом считаем
            count = model.objects.filter(**{self.parent_field: parent}).count()
        else:
            manager = model.objects.select_for_update()
            count = model.objects.count()
        try:
            orig = model.objects.get(pk=instance.pk)
        except model.DoesNotExist:
            ## новый элемент
            if not (0 < position <= count):
                position = count + 1
                setattr(instance, self.attname, position)
            return self._shift(manager=manager, field_name=self.attname, start=position, end=0, direction=1)
        orig_pos = getattr(orig, self.attname)
        if parent and getattr(orig, self.parent_field) != parent:
        ## parent есть, и он изменился
            ## задаем position после последнего
            setattr(instance, self.attname, count+1)
            ## "сшиваем" список оригинального parent-а
            manager = model.objects.select_for_update().filter(**{self.parent_field: getattr(orig, self.parent_field)})
            return self._shift(manager=manager, field_name=self.attname, start=orig_pos, end=0, direction=-1)
        elif position != orig_pos:
            ## parent не изменился или не указан, позиция изменилась
            if not 0 < position <= count:
                position = count
                setattr(instance, self.attname, position)
            if orig_pos < position:
                return self._shift(
                    manager=manager,
                    field_name=self.attname,
                    start=orig_pos+1,
                    end=position,
                    direction=-1)
            else:
                return self._shift(
                    manager=manager,
                    field_name=self.attname,
                    start=position,
                    end=orig_pos-1,
                    direction=1)

    def _post_delete_position(self, instance, *args, **kwargs):
        position, manager = \
            getattr(instance, self.attname), \
            instance.__class__.objects.select_for_update()
        if self.parent_field:
            print '%s.parent_field="%s"' % (self.__class__, self.parent_field)
            manager = manager.filter(**{
                self.parent_field: getattr(instance, self.parent_field)
            })
        self._shift(manager=manager, field_name=self.attname, start=position, end=0, direction=-1)

    @staticmethod
    def _shift(manager, field_name, start, end, direction):
        if 0 == end:
            return manager.filter(**{"%s__gte" % field_name: start}).update(**{field_name: F(field_name)+direction})
        else:
            return manager.select_for_update().filter(**{"%s__range" % field_name: (start, end)}).\
                update(**{field_name: F(field_name)+direction})
