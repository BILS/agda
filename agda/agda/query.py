from django.db import models, connection
from django.db.models.base import ModelBase
from django.db.models.query import QuerySet

from utils import get_columns, rows


class CustomQuerySetManager(models.Manager):
    # From here:
    # https://gist.github.com/1132844

    # http://docs.djangoproject.com/en/dev/topics/db/managers/#using-managers-for-related-object-access
    use_for_related_fields = True

    def __init__(self, qs_class=models.query.QuerySet):
        self.queryset_class = qs_class
        super(CustomQuerySetManager, self).__init__()

    def get_query_set(self):
        return self.queryset_class(self.model)

    def __getattr__(self, attr, *args):
        try:
            return getattr(self.__class__, attr, *args)
        except AttributeError:
            return getattr(self.get_query_set(), attr, *args)


class ManagingQuerySet(QuerySet):
    """Base QuerySet class for adding custom methods that are made
    available on both the manager and subsequent cloned QuerySets
    """

    @classmethod
    def as_manager(cls, ManagerClass=CustomQuerySetManager):
        return ManagerClass(cls)

# Fulltext search stuff-


def get_fulltext_indexes(model):
    indexes = model.fulltext_indexes
    if isinstance(indexes, (basestring, models.Field)):
        indexes = dict(default=(indexes,))
    elif isinstance(indexes, (tuple, list)):
        return dict(default=indexes)
    return indexes


def get_fulltext_index_columns(model, name='default'):
    return get_columns(model, get_fulltext_indexes(model)[name])


class MySQLFulltextSearchQuerySet(ManagingQuerySet):
    """A queryset with MySQL multicolumn fulltext index search support.

    Requires MySQL backend and MyISAM table with fulltext index. Use for
    example setup_fulltext_indexes() to create the index automatically.

    The fields to search must be specified using the fulltext_indexes
    attribute on the model. This can be either:

    1. a list of fields or field names, or
    2. an index name to field list dictionary to set up multiple named indexes.

    If index name is None or unspecified, it will be given the name 'default'.

    Examples:

    | fulltext_search_fields = [title, text]
    | fulltext_search_fields = ('title', 'text')
    | fulltext_search_fields = {None: (title, text),
    |                          'titles_only': title}

    """
    def search(self, query, index='default', by_relevance=False, relevance_attr='relevance'):
        meta = self.model._meta
        columns = get_fulltext_index_columns(self.model, index)
        _q = connection.ops.quote_name
        full_names = ["%s.%s" % (_q(meta.db_table), _q(column)) for column in columns]
        fulltext_columns = ", ".join(full_names)
        select = None
        select_params = None
        order_by = None
        where = ["MATCH(%s) AGAINST (%%s IN BOOLEAN MODE)" % fulltext_columns]
        params = [query]
        if by_relevance:
            select = {relevance_attr: "MATCH(%s) AGAINST (%%s)" % fulltext_columns}
            select_params = [query]
            order_by = ['-' + relevance_attr]
        return self.extra(select=select,
                          select_params=select_params,
                          where=where,
                          params=params,
                          order_by=order_by)


def setup_fulltext_index(model, fields, index_name='fulltext_default'):
    """Set up a MySQL fulltext index for a model.

    fields can be a list of fields or field names.

    This function will set ENGINE=MyISAM for the table (necessary for
    fulltext indexes) and create the fulltext index as specified, recreating
    it if necessary.
    """
    meta = model._meta
    _q = connection.ops.quote_name
    index_columns = get_columns(model, fields)
    cursor = connection.cursor()
    cursor.execute("SHOW TABLE STATUS WHERE name=%s", (meta.db_table,))
    engine = cursor.fetchone()[[c[0] for c in cursor.description].index('Engine')]
    if engine.lower() != 'myisam':
        cursor.execute('ALTER TABLE %s ENGINE=MyISAM' % _q(meta.db_table))
    sql = "SHOW INDEX IN %s WHERE key_name=%%s" % _q(meta.db_table)
    cursor.execute(sql, [index_name])
    i = [c[0] for c in cursor.description].index('Column_name')
    current_columns = [row[i] for row in rows(cursor)]
    if current_columns == index_columns:
        return
    print "Creating fulltext search index %s for %s" % (index_name, meta.db_table)
    if current_columns:
        sql = "DROP INDEX %s ON %s" % (_q(index_name), _q(meta.db_table))
        cursor.execute(sql)
    column_fullnames = ','.join(_q(name) for name in index_columns)
    sql = "CREATE FULLTEXT INDEX %s ON %s (%s)" % (_q(index_name), _q(meta.db_table), column_fullnames)
    cursor.execute(sql)


def setup_fulltext_indexes(sender, **kw):
    """Django signals callback to set up MySQL fulltext indexes.

    This function iterates through the fulltext_indexes attribute for any model
    in sender that has it, and calls setup_fulltext_index to ensure that the
    indexes are created.

    fulltext_indexes should be a list of fields or field names, or a index name
    to field list dictionary to set up multiple named indexes.
    """
    for name in dir(sender):
        model = getattr(sender, name)
        if not (isinstance(model, ModelBase) and hasattr(model, 'fulltext_indexes')):
            continue
        for name, fields in get_fulltext_indexes(model).items():
            setup_fulltext_index(model, fields, 'fulltext_' + name)
