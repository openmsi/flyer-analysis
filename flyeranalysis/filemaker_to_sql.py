"""A script to dynamically convert the FileMaker DB to entries in SQL tables

Contains a helper class and a "main" function to run from the command line

Typical usage:
    python -m filemaker_to_sql [sql_db_connection_string] [filemaker_ip_address]
"""

# imports
import pathlib
import logging
import json
import getpass
import datetime
import warnings
from argparse import ArgumentParser
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    insert,
    String,
    Float,
    Integer,
    ForeignKey,
    DateTime,
    select,
    and_,
    or_,
)
import fmrest


class FileMakerToSQL:
    """Manages translating FileMaker DB layouts/entries to SQL DB tables/rows

    Args:
        logger_stream_level:
            level for logger stream handler. If "NONE" no messages will be logged
            to the stream.
        logger_file_level:
            level for logger file handler. If "NONE" no messages will be logged
            to the file.
        logfile_path:
            path to the log file to use

    Raises:
        FileNotFoundError: the layout map json file doesn't exist
        RuntimeError: the layout map json file couldn't be parsed into a dictionary
    """

    # constants
    LOGGER_CHOICES = ["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NONE"]
    DEF_LOGGER_STREAM_LEVEL = "DEBUG"  # "INFO"
    DEF_LOGGER_FILE_LEVEL = "NONE"  # "WARNING"
    DEF_LOGFILE_PATH = pathlib.Path(
        f"./{pathlib.Path(__file__).name[:-len('.py')]}.log"
    )
    FMREST_SERVER_EXTRA_KWARGS = {"verify_ssl": False, "api_version": "v1"}
    FM_DB_NAME = "Laser Shock"
    FM_LAYOUT_MAP_FILEPATH = (
        pathlib.Path(__file__).resolve().parent / "filemaker_layout_map.json"
    )
    TYPE_HIERARCHY = [float, int, str]
    TYPE_MAP = {
        str: String,
        float: Float,
        int: Integer,
        datetime.datetime: DateTime,
    }

    @property
    def sql_db_table_names(self):
        "A list of all of the SQL DB table names defined in the FileMaker layout map"
        return [map_dict["sql_table_name"] for map_dict in self.fm_layout_map.values()]

    def __init__(
        self,
        logger_stream_level=DEF_LOGGER_STREAM_LEVEL,
        logger_file_level=DEF_LOGGER_FILE_LEVEL,
        logfile_path=DEF_LOGFILE_PATH,
    ):
        self.logger = self.__get_logger(
            logger_stream_level, logger_file_level, logfile_path
        )
        if not self.FM_LAYOUT_MAP_FILEPATH.is_file():
            self.__log_and_raise_exception(
                FileNotFoundError,
                f"ERROR: Layout map json file {self.FM_LAYOUT_MAP_FILEPATH} does not exist!",
            )
        try:
            with open(self.FM_LAYOUT_MAP_FILEPATH) as fm_layout_json_file:
                self.fm_layout_map = json.load(fm_layout_json_file)
        except Exception as exc:
            self.__log_and_raise_exception(
                RuntimeError,
                f"ERROR: failed to parse the JSON file at {self.FM_LAYOUT_MAP_FILEPATH}",
                raise_from=exc,
            )
        self.engine = None
        self.meta = None
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
            self.meta = MetaData()
            self.meta.reflect(bind=self.engine)
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
        test_server = self.__get_filemaker_server(list(self.fm_layout_map.keys())[0])
        test_server.logout()

    def drop_tables(self):
        "If any of the tables we're about to create exist already, drop them"
        tables_to_drop = [
            self.meta.tables[tname]
            for tname in self.meta.tables
            if tname in self.sql_db_table_names
        ]
        if len(tables_to_drop) > 0:
            self.logger.warning(
                "WARNING: Dropping tables: %s",
                ", ".join([table.name for table in tables_to_drop]),
            )
            self.meta.drop_all(bind=self.engine, tables=tables_to_drop)
        self.meta = MetaData()
        self.meta.reflect(bind=self.engine)

    def convert(self):
        """Dynamically creates tables and rows in them for every entry in each layout of
        the FileMaker DB

        Raises:
            RuntimeError: Something went wrong when trying to add entries to a table
        """
        for layout, map_dict in self.fm_layout_map.items():
            self.logger.info('Adding entries from the "%s" FileMaker Layout', layout)
            tablename = map_dict["sql_table_name"]
            fms = self.__get_filemaker_server(layout_name=layout)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                records_df = (fms.get_records(limit=100000)).to_df()
            if records_df.shape[0] < 1:
                warnmsg = (
                    f"WARNING: found {records_df.shape[0]} records in the "
                    f'"{layout}" layout! The "{tablename}" table will not be added.'
                )
                self.logger.warning(warnmsg)
                continue
            columns = self.__get_columns_from_fm_records(records_df, layout)
            new_table = Table(
                tablename,
                self.meta,
                *columns,
            )
            self.meta.create_all(bind=self.engine, tables=[new_table])
            entry_sets = self.__get_entry_sets_from_fm_records(records_df, layout)
            n_new_entries = 0
            try:
                with self.engine.connect() as conn:
                    for entry_list in entry_sets.values():
                        # if tablename == "launch_package":
                        #     for entry in entry_list:
                        #         n_new_entries += 1
                        #         _ = conn.execute(insert(new_table), [entry])
                        #         conn.commit()
                        # else:
                        n_new_entries += len(entry_list)
                        _ = conn.execute(insert(new_table), entry_list)
                    conn.commit()
            except Exception as exc:
                self.__log_and_raise_exception(
                    RuntimeError,
                    f"ERROR: failed adding entries to the {tablename} table!",
                    raise_from=exc,
                )
            self.logger.debug(
                "Added %s entries to the %s table", n_new_entries, tablename
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
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fms.login()
        except Exception as exc:
            errmsg = (
                "ERROR: failed to authenticate to the FileMaker Database "
                f'"{layout_name}" layout (IP address {self.fm_ip_address}) '
            )
            self.__log_and_raise_exception(RuntimeError, errmsg, raise_from=exc)
        return fms

    def __get_python_type_for_column(self, column_records, layout, column_name):
        """Return the Python type that every entry in a particular column should be cast to

        Args:
            column_records: a single column of a Pandas dataframe of FileMaker record objects
            layout: the name of the FileMaker layout from which the records were retrieved
            column_name: the name of the column in question

        Returns: The Python data type that entries for this column should be cast to
        """
        if column_name in self.fm_layout_map[layout]["custom_columns"]:
            for col_unique in self.fm_layout_map[layout]["custom_columns"][column_name]:
                if col_unique == "astype-datetime":
                    return datetime.datetime
        column_python_type = None
        all_column_types = set(list(column_records.map(type)))
        for python_type in self.TYPE_HIERARCHY:
            if python_type in all_column_types:
                column_python_type = python_type
                break
        return column_python_type

    def __get_columns_from_fm_records(self, records, layout):
        """Given a dataframe of FileMaker records and the name of the layout they came
        from, return a list of SQLAlchemy Column objects that should be used in its
        corresponding SQL Table

        Args:
            records: a Pandas dataframe of FileMaker record objects
            layout: the name of the FileMaker layout from which the records were retrieved

        Returns: A list of SQLAlchemy Column objects defining the new SQL table to be added
        """
        all_columns = []
        for column_name in records.columns:
            col_uniques = []
            if column_name in self.fm_layout_map[layout]["custom_columns"]:
                col_uniques = self.fm_layout_map[layout]["custom_columns"][column_name]
            # skip any columns that should be ignored
            if "ignore" in col_uniques:
                continue
            # set the args for the column and type constructors
            col_extra_args = []
            col_kwargs = {}
            if column_name == self.fm_layout_map[layout]["pk_key"]:
                col_kwargs["primary_key"] = True
            if "unique" in col_uniques:
                col_kwargs["unique"] = True
            for col_unique in col_uniques:
                if col_unique == "not_null":
                    col_kwargs["nullable"] = False
                elif col_unique == "unique":
                    col_kwargs["unique"] = True
                elif col_unique.startswith("fk"):
                    col_extra_args.append(ForeignKey(col_unique.split("-")[-1]))
            column_python_type = self.__get_python_type_for_column(
                records[column_name], layout, column_name
            )
            column_type = self.TYPE_MAP[column_python_type]
            type_kwargs = {}
            if column_type == String:
                if column_name.lower().replace(" ", "_") in (
                    "glass_name",
                    "glass_name_reference",
                    "launch_id",
                ):
                    type_kwargs["length"] = 256
                else:
                    type_kwargs["length"] = records[column_name].str.len().max()
            # append the new column
            all_columns.append(
                Column(
                    column_name.lower().replace(" ", "_"),
                    column_type(**type_kwargs),
                    *col_extra_args,
                    **col_kwargs,
                )
            )
        # for the experiment layout, add an extra column for the metadata_links FK
        if layout == "Experiment":
            all_columns.append(
                Column(
                    "video_metadata_link_ID",
                    Integer,
                    ForeignKey("metadata_links.ID"),
                )
            )
        return all_columns

    def __get_entry_sets_from_fm_records(self, records, layout):
        """Given a dataframe of FileMaker records and the name of the layout they came from,
        return a dictionary of rows that should be added to the corresponding SQL table.

        The return value is a dictionary where the keys are sets (cast to strings) of
        non-null column values, and the values are lists of dictionaries representing
        new rows to add.

        Args:
            records: list of FileMaker records from the given layout
            layout: the name of the FileMaker layout from which the records were retrieved

        Returns: A dictionary of lists of new entries to add
        """
        entry_sets = {}
        column_python_types = {
            column_name: self.__get_python_type_for_column(
                records[column_name], layout, column_name
            )
            for column_name in records.columns
        }
        for _, row in records.iterrows():
            entry = {}
            for column_name in records.columns:
                val = row[column_name]
                if isinstance(val, str):
                    val = val.strip()
                if val in ("", " ", "N/A", "?"):
                    continue
                # some custom adjustments below
                if (
                    isinstance(val, str)
                    and column_name == "PreAmp Output Power"
                    and "-" in val
                ):
                    oldval = val
                    val = str(
                        0.5 * (float(val.split("-")[0]) + float(val.split("-")[1]))
                    )
                    self.logger.warning(
                        "Adjusted %s value from %s to %s", column_name, oldval, val
                    )
                if column_python_types[column_name] == datetime.datetime:
                    sqlval = datetime.datetime.strptime(val, "%m/%d/%Y")
                else:
                    try:
                        sqlval = column_python_types[column_name]()
                    except:
                        print(f"val = {val}, colname = {column_name}")
                        raise
                    sqlval = column_python_types[column_name](val)
                entry[column_name.lower().replace(" ", "_")] = sqlval
            # for the experiment layout, add the metadata link FK
            if layout == "Experiment":
                links_table = self.meta.tables["metadata_links"]
                constraints = []
                if "experiment_day_counter" in entry:
                    constraints.append(
                        links_table.c.experiment_day_counter
                        == entry["experiment_day_counter"]
                    )
                if "camera_filename" in entry:
                    constraints.append(
                        links_table.c.camera_filename == entry["camera_filename"]
                    )
                if len(constraints) > 0:
                    and_where_clause = None
                    or_where_clause = None
                    if len(constraints) == 1:
                        and_where_clause = and_(
                            links_table.c.datestamp == entry["date"], constraints[0]
                        )
                        or_where_clause = and_where_clause
                    elif len(constraints) == 2:
                        and_where_clause = and_(
                            links_table.c.datestamp == entry["date"], *constraints
                        )
                        or_where_clause = and_(
                            links_table.c.datestamp == entry["date"], or_(*constraints)
                        )
                    else:
                        self.__log_and_raise_exception(
                            RuntimeError,
                            (
                                f"Got {len(constraints)} constraints for a query "
                                "to the metadata_links table (expected either 1 or 2)!"
                            ),
                        )
                    and_stmt = select(links_table.c.ID).where(and_where_clause)
                    or_stmt = select(links_table.c.ID).where(or_where_clause)
                    with self.engine.connect() as conn:
                        res = conn.execute(and_stmt).all()
                    if (res is None) or (len(res) == 0):
                        with self.engine.connect() as conn:
                            res = conn.execute(or_stmt).all()
                    if len(res) == 1:
                        entry["video_metadata_link_ID"] = res[0].ID
                    elif len(res) > 1:
                        warnmsg = (
                            f"WARNING: found {len(res)} matching metadata links "
                            f"for experiment entry {entry}. "
                            "This entry will not have a metadata link added!"
                        )
                        self.logger.warning(warnmsg)
            keysetstr = str(set(list(entry.keys())))
            if keysetstr not in entry_sets:
                entry_sets[keysetstr] = []
            entry_sets[keysetstr].append(entry)
        return entry_sets


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
