from django.contrib.messages import DEFAULT_TAGS as message_default_tags
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe, SafeData
from django import template

register = template.Library()


def mailto_link(text, autoescape=None):
    if isinstance(text, SafeData):
        input_is_safe = True
    else:
        input_is_safe = False
    if autoescape and not input_is_safe:
        esc = conditional_escape
    else:
        esc = lambda x: x
    text = esc(unicode(text).strip())
    if text:
        res = u'<a href="mailto:%s">%s</a>' % (text, text)
    else:
        res = u''
    return mark_safe(res)
mailto_link.needs_autoescape = True
register.filter('mailto_link', mailto_link)

message_severity_levels = ('error', 'warning', 'success', 'info',)


def message_severity_label(value):
    for tag in reversed(message_default_tags.values()):
        if tag in value:
            return tag.capitalize() + u":"
register.filter('message_severity_label', message_severity_label)


def agda_date(datetime):
    if not datetime:
        return ''
    return datetime.strftime('%Y%m%d-%H:%M:%S')
register.filter('agda_date', agda_date)
