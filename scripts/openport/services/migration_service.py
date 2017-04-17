__author__ = 'jan'
from sqlalchemy import create_engine

from alembic.script import ScriptDirectory
from alembic.operations import Operations
from alembic.migration import MigrationContext
from alembic import util, autogenerate as autogen
from openport.services.osinteraction import OsInteraction, getInstance as get_osinteraction_instance
from openport.services.logger_service import get_logger

logger = get_logger(__name__)

def get_script_directory():
    path = OsInteraction.resource_path('alembic')
    logger.debug('alembic path: %s' % path)
    script_directory = ScriptDirectory(path)
    return script_directory


def get_migration_context(db_location, script_directory, opts={}):
    url = "sqlite:///%s" % db_location
    engine = create_engine(url)
    conn = engine.connect()
    default_opts = {'script': script_directory}
    context = MigrationContext.configure(conn, opts=dict(default_opts, **opts))
    return context


def get_current_db_revision(db_location):
    context = get_migration_context(db_location, None)

    current_rev = context.get_current_revision()
    print "current db revision:  %s " % current_rev
    return current_rev


def update_if_needed(db_location):
    logger.debug('update_if_needed')
    script_directory = get_script_directory()
    def upgrade(rev, context):
        revision = 'head'
        return script_directory._upgrade_revs(revision, rev)

    context = get_migration_context(db_location, script_directory, {'fn': upgrade})

    from alembic.op import _install_proxy
    op = Operations(context)
    _install_proxy(op)

    with context.begin_transaction():
        context.run_migrations()
    context.connection.close()

def create_migrations(db_location):
    script_directory = get_script_directory()
    template_args = {
       # 'config': config  # Let templates use config for
                          # e.g. multiple databases
    }

    def retrieve_migrations(rev, context):
        if set(script_directory.get_revisions(rev)) != \
                set(script_directory.get_revisions("heads")):
            raise util.CommandError("Target database is not up to date.")

        imports = set()
        autogen._produce_migration_diffs(context, template_args, imports)
        return []

    from openport.services import dbhandler

    metadata = dbhandler.Base.metadata

    context = get_migration_context(db_location, script_directory, {
        'fn': retrieve_migrations,
        'target_metadata': metadata,
        'upgrade_token': 'upgrades',
        'downgrade_token': 'downgrades',
        'alembic_module_prefix': 'op.',
        'sqlalchemy_module_prefix': 'sa.',
    })
    context.run_migrations()

    path = OsInteraction.resource_path('alembic', 'versions')

    message = ''
    script_directory.generate_revision(
        util.rev_id(), message, refresh=True,
        head='head', splice=False, branch_labels=None,
        version_path=path, **template_args)

    get_osinteraction_instance().run_shell_command('git add %s' % path)


