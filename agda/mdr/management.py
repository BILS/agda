from django.db.models.signals import post_syncdb
from agda.query import setup_fulltext_indexes
import models as mdr_models

post_syncdb.connect(setup_fulltext_indexes, sender=mdr_models)

try:
    from south.signals import post_migrate

    def callback(sender, app=None, **kw):
        if app != 'mdr':
            return
        setup_fulltext_indexes(mdr_models)
    post_migrate.connect(callback)
except ImportError:
    pass
