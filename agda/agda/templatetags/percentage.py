from django import template

register = template.Library()


@register.filter
def percentage(decimal, round=2):
    return format(decimal, ".%d%%" % round)
