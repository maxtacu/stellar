import argparse
import sys
from time import sleep

import humanize

from app import Stellar
from datetime import datetime
from stellar.exceptions import InvalidConfig, MissingConfig


class CommandApp(object):
    def __init__(self):
        parser = argparse.ArgumentParser(
            description='Lightning fast database snapshotting for development',
        )
        parser.add_argument(
            'command',
            help='Subcommand to run',
            choices=[unicode(x) for x in dir(self) if not x.startswith('_')],
        )
        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            print 'Unrecognized command'
            parser.print_help()
            exit(1)
        getattr(self, args.command)()

    def gc(self):
        app = Stellar()
        for snapshot in app.get_orphan_snapshots():
            print "Removing %s" % snapshot.table_name
            app.remove_snapshot(snapshot)
        print "Garbage collection complete"

    def snapshot(self):
        parser = argparse.ArgumentParser(
            description='Take a snapshot of the database'
        )
        parser.add_argument('name', nargs='?', default='default')
        args = parser.parse_args(sys.argv[2:])

        print "Snapshotting tracked databases: %s" % ', '.join(
            config['tracked_databases']
        )
        app = Stellar()
        if app.get_snapshot(args.name):
            print "Already exist"
        else:
            app.create_snapshot(args.name)

    def list(self):
        argparse.ArgumentParser(
            description='List snapshots'
        )

        snapshots = Stellar().get_snapshots()

        print '\n'.join(
            '%s %s ago' % (
                s.name,
                humanize.naturaltime(datetime.utcnow() - s.created_at)
            )
            for s in snapshots
        )

    def restore(self):
        parser = argparse.ArgumentParser(
            description='Restore database from snapshot'
        )
        parser.add_argument('name', nargs='?')
        args = parser.parse_args(sys.argv[2:])

        app = Stellar()

        if not args.name:
            snapshot = app.get_latest_snapshot()
            if not snapshot:
                print (
                    "Couldn't find any snapshots for project %s" %
                    config['project_name']
                )
                return
        else:
            snapshot = app.get_snapshot(args.name)
            if not snapshot:
                print (
                    "Couldn't find snapshot with name %s.\n"
                    "You can list snapshots with 'stellar list'" % args.name
                )

        # Check if slaves are ready
        if not snapshot.is_slave_ready:
            sys.stdout.write('Waiting for background process to finish')
            sys.stdout.flush()
            while not snapshot.is_slave_ready:
                sys.stdout.write('.')
                sys.stdout.flush()
                sleep(1)
                app.stellar_db.session.refresh(snapshot)
            print ''

        app.restore(snapshot)
        print "Restore complete."

    def remove(self):
        parser = argparse.ArgumentParser(
            description='Removes spesified snapshot'
        )
        parser.add_argument('name', default='')
        args = parser.parse_args(sys.argv[2:])

        app = Stellar()

        if not args.name:
            assert False
        else:
            snapshot = app.get_snapshot(args.name)
        if not snapshot:
            print "Couldn't find snapshot %s" % args.name
            return

        print "Deleting snapshot %s" % args.name
        app.remove_snapshot(snapshot)
        print "Deleted"

    def init(self):
        name = raw_input("Please enter project name (ex. myproject): ")
        url = raw_input(
            "Please enter database url (ex. postgresql://localhost:5432/): "
        )
        db_name = raw_input(
            "Please enter project database name (ex. myproject): "
        )

        project_file = open('stellar.yaml', 'w')
        project_file.write(
            """
project_name: '%(name)s'
tracked_databases: ['%(db_name)s']
url: '%(url)s'
stellar_url: '%(url)sstellar_data'
            """.strip() %
            {
                'name': name,
                'url': url,
                'db_name': db_name
            }
        )
        project_file.close()
        print "Wrote stellar.yaml"


def main():
    try:
        CommandApp()
    except MissingConfig:
        print "You don't have stellar.yaml configuration yet."
        print "Initialize it by running: stellar init"
    except InvalidConfig, e:
        print "Your stellar.yaml configuration is wrong: %s" % e.message

if __name__ == '__main__':
    main()
    #
    # stellar
    # 1. Snapshot current database
    # stellar snapshot <name> (--git)
    # stellar rollback <name> (--git)
    # stellar list
    # stellar remove
