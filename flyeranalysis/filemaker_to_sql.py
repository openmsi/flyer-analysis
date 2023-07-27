"""A script to dynamically convert the FileMaker DB to entries in SQL tables

Contains a helper class and a "main" function to run from the command line

Typical usage:
    python -m filemaker_to_sql [sql_db_connection_string] [filemaker_ip_address]
"""

# imports
import pathlib
import logging
import getpass
from argparse import ArgumentParser
from sqlalchemy import create_engine, MetaData
import fmrest


class FileMakerToSQL:
    """Manages translating FileMaker DB layouts/entries to SQL DB tables/rows

    TODO:finish this docstring"""

    # constants
    LOGGER_CHOICES = ["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NONE"]
    DEF_LOGGER_STREAM_LEVEL = "DEBUG"  # "INFO"
    DEF_LOGGER_FILE_LEVEL = "NONE"  # "WARNING"
    DEF_LOGFILE_PATH = pathlib.Path(
        f"./{pathlib.Path(__file__).name[:-len('.py')]}.log"
    )
    FMREST_SERVER_EXTRA_KWARGS = {"verify_ssl": False, "api_version": "v1"}
    FM_DB_NAME = "Laser Shock"
    FM_LAYOUT_NAMES = [
        "Glass ID",
        "Foil ID",
        "Epoxy ID",
        "Spacer ID",
        "Flyer Cutting Program",
        "Spacer Cutting Program",
        "Flyer Stack",
        "Sample",
        "Launch Package",
        "Experiment",
    ]
    SQL_DB_TABLE_NAMES = [
        fm_layout_name.replace(" ", "") for fm_layout_name in FM_LAYOUT_NAMES
    ]

    def __init__(
        self,
        logger_stream_level=DEF_LOGGER_STREAM_LEVEL,
        logger_file_level=DEF_LOGGER_FILE_LEVEL,
        logfile_path=DEF_LOGFILE_PATH,
    ):
        self.logger = self.__get_logger(
            logger_stream_level, logger_file_level, logfile_path
        )
        self.engine = None
        self.fm_ip_address = None
        self.fm_uname = None
        self.fm_pword = None

    def connect_to_dbs(self, connection_str, filemaker_ip, verbose=False):
        """Initialize authentication information for the SQL and FileMaker DBs

        Creates a SQLAlchemy engine for interacting with the SQL DB. Gets the user's
        JHED username and password and tests authenticating to a layout of the
        FileMaker DB.

        Args:
            connection_str: The string for connecting to the output SQL DB using SQLAlchemy
            filemaker_ip: The IP Address from which the FileMaker DB is reachable
            verbose: If True, a verbose SQLAlchemy Engine will be created

        Raises:
            ValueError: Connecting to the SQL DB failed
            RuntimeError: Authenticating to the FileMaker DB failed
        """
        try:
            self.engine = create_engine(connection_str, echo=verbose)
        except Exception as exc:
            errmsg = (
                "ERROR: failed to connect to sql database "
                f"with connection string {connection_str}"
            )
            self.__log_and_raise_exception(ValueError, errmsg, raise_from=exc)
        self.fm_ip_address = filemaker_ip
        if not self.fm_ip_address.startswith("https://"):
            self.fm_ip_address = f"https://{self.fm_ip_address}"
        self.fm_uname = input("Please enter your JHED username: ").rstrip()
        self.fm_pword = getpass.getpass(
            f"Please enter the JHED password for {self.fm_uname}: "
        )
        test_server = self.__get_filemaker_server(self.FM_LAYOUT_NAMES[0])
        test_server.logout()

    def drop_tables(self):
        "If any of the tables we're about to create exist already, drop them"
        meta = MetaData()
        meta.reflect(bind=self.engine)
        tables_to_drop = [
            meta.tables[tname]
            for tname in meta.tables
            if tname in self.SQL_DB_TABLE_NAMES
        ]
        if len(tables_to_drop) > 0:
            self.logger.warning(
                "WARNING: Dropping tables: %s",
                ", ".join([table.name for table in tables_to_drop]),
            )
            meta.drop_all(bind=self.engine, tables=tables_to_drop)

    def convert(self):
        """TODO: write this docstring"""
        for layout_name in self.FM_LAYOUT_NAMES:
            self.logger.info(
                'Adding entries from the "%s" FileMaker Layout', layout_name
            )
        self.logger.info("Done!")

    @classmethod
    def get_command_line_options(cls, args=None):
        """Return the command line options given an (optional) list of args

        Args:
            args: a list of arguments to pass to the parser instead of using sys.argv

        Returns: A namespace of parsed arguments
        """
        parser = ArgumentParser()
        parser.add_argument(
            "connection_string",
            help="The SQLAlchemy connection string detailing the database to use",
        )
        parser.add_argument(
            "filemaker_ip",
            help="The IP address from which the FileMaker Database can be reached",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Add this flag to use a verbose SQLAlchemy engine",
        )
        parser.add_argument(
            "--logger_stream_level",
            choices=cls.LOGGER_CHOICES,
            default=cls.DEF_LOGGER_STREAM_LEVEL,
            help=(
                "The level for the logger stream handler. "
                "Messages below this level will not be logged to the console. "
                'Pass "NONE" to disable logging to the console. '
                f"(default = {cls.DEF_LOGGER_STREAM_LEVEL})"
            ),
        )
        parser.add_argument(
            "--logger_file_level",
            choices=cls.LOGGER_CHOICES,
            default=cls.DEF_LOGGER_FILE_LEVEL,
            help=(
                "The level for the logger file handler. "
                "Messages below this level will not be logged to the file. "
                'Pass "NONE" to disable logging to a file. '
                f"(default = {cls.DEF_LOGGER_FILE_LEVEL})"
            ),
        )
        parser.add_argument(
            "--logfile_path",
            type=pathlib.Path,
            default=cls.DEF_LOGFILE_PATH,
            help=f"Path to the program's log file (default = {cls.DEF_LOGFILE_PATH})",
        )
        return parser.parse_args(args)

    ####################### PRIVATE FUNCTIONS #######################

    def __get_logger(self, stream_level, file_level, file_path):
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.NOTSET + 1)
        logging_formatter = logging.Formatter(
            "[%(name)s %(asctime)s] %(message)s", "%Y-%m-%d %H:%M:%S"
        )
        if stream_level and stream_level != "NONE":
            streamhandler = logging.StreamHandler()
            streamhandler.setLevel(getattr(logging, stream_level))
            streamhandler.setFormatter(logging_formatter)
            logger.addHandler(streamhandler)
        if file_level and file_level != "NONE":
            if not file_path.parent.exists:
                file_path.parent.mkdir(parents=True)
            filehandler = logging.FileHandler(file_path)
            filehandler.setLevel(getattr(logging, file_level))
            filehandler.setFormatter(logging_formatter)
            logger.addHandler(filehandler)
        return logger

    def __log_and_raise_exception(self, exc_type, message, raise_from=None):
        try:
            raise exc_type(message) from raise_from
        except Exception as exc:
            self.logger.error(message, exc_info=exc)
            raise

    def __get_filemaker_server(self, layout_name):
        "Return a new FileMaker Server instance authenticated to the specified layout"
        try:
            fms = fmrest.Server(
                self.fm_ip_address,
                user=self.fm_uname,
                password=self.fm_pword,
                database=self.FM_DB_NAME,
                layout=layout_name,
                **self.FMREST_SERVER_EXTRA_KWARGS,
            )
            fms.login()
        except Exception as exc:
            errmsg = (
                "ERROR: failed to authenticate to the FileMaker Database "
                f'"{layout_name}" layout (IP address {self.fm_ip_address}) '
            )
            self.__log_and_raise_exception(RuntimeError, errmsg, raise_from=exc)
        return fms


def main(args=None):
    """Run the helper functions above to convert everything in
    the given FileMaker DB to entries in tables in the SQL DB
    """
    options = FileMakerToSQL.get_command_line_options(args)
    sql_converter = FileMakerToSQL(
        options.logger_stream_level,
        options.logger_file_level,
        options.logfile_path,
    )
    sql_converter.connect_to_dbs(
        options.connection_string,
        options.filemaker_ip,
        verbose=options.verbose,
    )
    sql_converter.drop_tables()
    sql_converter.convert()


if __name__ == "__main__":
    main()
