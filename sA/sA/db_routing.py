import time
import logging
from django.db import connections, OperationalError

logger = logging.getLogger(__name__)

class PostgreSQLRouter:
    def __init__(self):
        self.replica_list = ['replica1', 'replica2']
        self.write_db = 'default'                       # Initially, the master is the default DB
        self.read_db_index = 0                          # Initially, route reads to replica1

    def db_for_read(self, model, **hints):
        """
        Routes read queries to the replicas, retrying if the connection fails.
        """
        for _ in range(len(self.replica_list)):
            try:
                read_db = self.replica_list[self.read_db_index]
                if self.is_connection_healthy_no_reconnect(read_db):
                    return read_db
                else:
                    raise OperationalError(f"Replica {read_db} is unavailable.")
            except OperationalError as e:
                logger.error(f"Error reading from replica {read_db}: {e}")
                self.handle_db_failure('replica')
            except Exception as e:
                logger.error(f"Error reading from replica {read_db}: {e}")

        logger.critical("No replicas are available for reading. Falling back to master.")
        return self.write_db

    def db_for_write(self, model, **hints):
        """
        Routes write queries to the master, retrying if the connection fails.
        """
        while True:
            try:
                if self.is_connection_healthy_no_reconnect(self.write_db):
                    print(f"Writing to {self.write_db}")
                    return self.write_db
                else:
                    raise OperationalError(f"Master {self.write_db} is unavailable.")
            except OperationalError as e:
                logger.error(f"Error writing to master {self.write_db}: {e}")
                self.handle_db_failure('master')
            except Exception as e:
                logger.error(f"Error writing to master {self.write_db}: {e}")

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure migrations always run on the master DB.
        """
        return db == self.write_db

    def handle_db_failure(self, db_type):
        """
        Handles database failure by reconfiguring the database routing.
        - For a master failure: promote the first replica to master, route reads to the next replica.
        - For a replica failure: remove it from the replica list and route reads to the next available replica.
        """
        if db_type == 'master':
            self.promote_replica_to_master()
        elif db_type == 'replica':
            self.remove_failed_replica()

    def promote_replica_to_master(self):
        """
        Promote the first replica in the list to be the new master and reroute reads to the second replica.
        """
        if self.replica_list:
            # Promote the first replica
            new_master = self.replica_list.pop(0)
            self.write_db = new_master
            self.read_db_index = 0  # Route reads to the next available replica
            logger.info(f"Master DB failed. Promoting {self.write_db} to be the new master.")
        else:
            logger.critical("No replicas are available to promote as the new master.")

    def remove_failed_replica(self):
        """
        Remove the failed replica from the list and reroute reads to the next available replica.
        """
        if self.replica_list:
            failed_replica = self.replica_list.pop(self.read_db_index)
            logger.info(f"Replica {failed_replica} removed from the replica list.")
            if self.replica_list:
                self.read_db_index %= len(self.replica_list)  # Adjust index to avoid out-of-bounds
            else:
                logger.warning("No replicas available for reading.")
        else:
            logger.critical("No replicas left to handle.")

    def is_connection_healthy_no_reconnect(self, db_alias):
        """
        Check if the database connection is healthy without reconnecting.
        """
        try:
            connection = connections[db_alias]
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()

            return True
        except OperationalError:
            return False
        except Exception as e:
            return False