"""Main runnable for adding entries to the flyer analysis DB using a stream processor

Typical usage:
    FlyerAnalysisStreamProcessor --db_connection_str [connection_string] --topic_name [topic]
"""
# imports
import datetime
import threading
from io import BytesIO
import numpy as np
import pandas as pd
from PIL import Image
from sqlalchemy import create_engine, inspect, select, and_
from sqlalchemy.orm import sessionmaker, scoped_session
from openmsistream import DataFileStreamProcessor
from .orm_base import ORMBase
from .metadata_link_entry import MetadataLinkEntry
from .flyer_analysis_entry import FlyerAnalysisEntry
from .flyer_image_entry import FlyerImageEntry
from .flyer_detection import Flyer_Detection, FlyerCharacteristics


class FlyerAnalysisStreamProcessor(DataFileStreamProcessor):
    """
    Run flyer analysis for all .bmp images in a topic
    and add their results to an output file or database

    The original .bmp image and the analysis result image will be
    stored in a secondary table if output is going to a DB
    """

    # All the Table objects associated with the DB
    ALL_TABLES = [
        FlyerAnalysisEntry.__table__,
        FlyerImageEntry.__table__,
        MetadataLinkEntry.__table__,
    ]

    def __init__(
        self,
        config_file,
        topic_name,
        *,
        db_connection_str=None,
        drop_existing=False,
        verbose=False,
        **other_kwargs,
    ):
        super().__init__(config_file, topic_name, **other_kwargs)
        # either create an engine to interact with a DB or store the path to the output file
        self._engine = None
        self._output_file = None
        analysis_table_name = FlyerAnalysisEntry.__tablename__
        if db_connection_str is not None:
            # if a connection string was given, connect to the DB
            try:
                extra_kwargs = {}
                if db_connection_str.startswith("mssql"):
                    extra_kwargs["deprecate_large_types"] = True
                self._engine = create_engine(
                    db_connection_str, echo=verbose, **extra_kwargs
                )
                self._scoped_session = scoped_session(sessionmaker(bind=self._engine))
                self._sessions_by_thread_ident = {}
            except Exception as exc:
                errmsg = (
                    "ERROR: failed to connect to database using connection string "
                    f"{db_connection_str}! Will re-reraise original exception."
                )
                self.logger.error(errmsg, reraise=True, exc_info=exc)
            # drop and recreate tables if requested
            if drop_existing:
                self.logger.info("Dropping and recreating tables")
                self.__drop_existing_tables()
                self.__create_tables()
            # create tables in the DB if any of them haven't been created yet
            inspector = inspect(self._engine)
            for table_name in [table.name for table in self.ALL_TABLES]:
                if not inspector.has_table(table_name):
                    self.__create_tables()
                    break
        else:
            # if no connection string was given, set the path to the single output file
            self._output_file = self._output_dir / f"{analysis_table_name}.csv"

    def _process_downloaded_data_file(self, datafile, lock):
        """
        Run the flyer analysis on the downloaded data file

        returns None if processing was successful, an Exception otherwise
        """
        if not datafile.filename.endswith(".bmp"):
            return None
        try:
            # first, if we're writing to a DB, check if the relative filepath
            # has already been written
            if self._engine is not None and self.__entry_exists(datafile, lock):
                return None
            result = None
            analyzer = Flyer_Detection()
            img = np.asarray(Image.open(BytesIO(datafile.bytestring)))
            # filtering the image sometimes fails, use a special exit code in this case
            try:
                filtered_image = analyzer.filter_image(img)
            except Exception:
                result = FlyerCharacteristics()
                result.rel_filepath = datafile.relative_filepath
                result.exit_code = 8
            if not result:
                result = analyzer.radius_from_lslm(
                    filtered_image,
                    datafile.relative_filepath,
                    self._output_dir,
                    min_radius=0,
                    max_radius=np.inf,
                    save_output_file=False,
                )
            if self._output_file is not None:
                self.__write_result_to_csv(result, lock)
            elif self._engine is not None:
                self.__write_result_to_db(result, datafile.bytestring, lock)
        except Exception as exc:
            return exc
        return None

    def _on_shutdown(self):
        super()._on_shutdown()
        self._engine.dispose()

    def __drop_existing_tables(self):
        """
        Drop the table in the database
        """
        ORMBase.metadata.drop_all(bind=self._engine, tables=self.ALL_TABLES)

    def __create_tables(self):
        """
        Create the table in the database
        """
        ORMBase.metadata.create_all(bind=self._engine, tables=self.ALL_TABLES)

    def __write_result_to_csv(self, result, lock):
        """
        Write a given result to the output CSV file
        """
        data = vars(result)
        data_frame = pd.DataFrame([data])
        with lock:
            if self._output_file.is_file():
                data_frame.to_csv(
                    self._output_file, mode="a", index=False, header=False
                )
            else:
                data_frame.to_csv(self._output_file, mode="w", index=False, header=True)

    def __entry_exists(self, datafile, lock):
        """
        Return True if there's already an entry for the given datafile's relative filepath
        (in case there are duplicate files in the topic)
        """
        stmt = select(FlyerAnalysisEntry.ID).where(
            FlyerAnalysisEntry.rel_filepath == str(datafile.relative_filepath)
        )
        with lock:
            with self._engine.connect() as conn:
                result = conn.execute(stmt).first()
            if result:
                return True
        return False

    def __get_metadata_link_id(self, result, lock, session):
        """
        Return the ID of a metadata link entry created for the video containing the given
        frame result. Creates the record if necessary.
        """
        # Determine the fields for the entry from the relative filepath
        fields = MetadataLinkEntry.get_link_fields_from_relative_filepath(
            result.rel_filepath
        )
        # Figure out the conditions for the query
        conditions = []
        if fields["datestamp"]:
            conditions.append(MetadataLinkEntry.datestamp == fields["datestamp"])
        if fields["experiment_day_counter"]:
            conditions.append(
                MetadataLinkEntry.experiment_day_counter
                == fields["experiment_day_counter"]
            )
        if fields["camera_filename"]:
            conditions.append(
                MetadataLinkEntry.camera_filename == fields["camera_filename"]
            )
        # At least one field must be determined
        if len(conditions) < 1:
            return None
        stmt = select(MetadataLinkEntry.ID).where(and_(*conditions))
        with lock:
            # If a matching entry already exists, return its ID
            with self._engine.connect() as conn:
                result = conn.execute(stmt).first()
            if result:
                return result[0]
            # If not, create and commit the entry and return its ID
            new_entry = MetadataLinkEntry(**fields)
            session.add(new_entry)
            session.commit()
            return new_entry.ID

    def __write_result_to_db(self, result, img_bytestring, lock):
        """
        Write a given result to the output database
        """
        # figure out the session to use
        thread_id = threading.get_ident()
        if thread_id not in self._sessions_by_thread_ident:
            with lock:
                self._sessions_by_thread_ident[thread_id] = self._scoped_session()
        # get the ID of the video metadata entry for this frame, adding it if necessary
        metadata_link_id = self.__get_metadata_link_id(
            result, lock, self._sessions_by_thread_ident[thread_id]
        )
        # add the analysis result entry
        analysis_entry = FlyerAnalysisEntry.from_id_and_result(metadata_link_id, result)
        self._sessions_by_thread_ident[thread_id].add(analysis_entry)
        self._sessions_by_thread_ident[thread_id].commit()
        # add the image entry
        image_entry = FlyerImageEntry.from_id_img_and_result(
            analysis_entry.ID, img_bytestring, result
        )
        self._sessions_by_thread_ident[thread_id].add(image_entry)
        self._sessions_by_thread_ident[thread_id].commit()

    @classmethod
    def run_from_command_line(cls, args=None):
        """
        Run the stream-processed analysis code from the command line
        """
        # make the argument parser
        parser = cls.get_argument_parser()
        parser.add_argument(
            "--db_connection_str",
            help=(
                "A string to use for connecting to a database to hold the output "
                "(SQLAlchemy format). Partial output will go in a .csv file if "
                "this argument is not given."
            ),
        )
        parser.add_argument(
            "--drop_existing",
            action="store_true",
            help=(
                "Add this flag to drop and recreate any existing flyer analysis/image "
                "tables in the database on startup"
            ),
        )
        parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Add this flag to use a verbose SQLAlchemy engine",
        )
        args = parser.parse_args(args=args)
        # make the stream processor
        flyer_analysis = cls(
            args.config,
            args.topic_name,
            db_connection_str=args.db_connection_str,
            drop_existing=args.drop_existing,
            verbose=args.verbose,
            output_dir=args.output_dir,
            filepath_regex=args.download_regex,
            n_threads=args.n_threads,
            update_secs=args.update_seconds,
            consumer_group_id=args.consumer_group_id,
            streamlevel=args.logger_stream_level,
            filelevel=args.logger_file_level,
        )
        # start the processor running
        run_start = datetime.datetime.now()
        flyer_analysis.logger.info(
            f"Listening to the {args.topic_name} topic for flyer image files to analyze"
        )
        (
            n_msgs_read,
            n_msgs_proc,
            n_files_proc,
            proc_filepaths,
        ) = flyer_analysis.process_files_as_read()
        flyer_analysis.close()
        run_stop = datetime.datetime.now()
        # shut down when that function returns
        msg = "Flyer analysis stream processor "
        if args.output_dir is not None:
            msg += f"writing to {args.output_dir} "
        msg += "shut down"
        flyer_analysis.logger.info(msg)
        msg = f"{n_msgs_read} total messages were consumed"
        if n_files_proc > 0:
            msg += (
                f", {n_msgs_proc} messages were successfully processed,"
                f" and {n_files_proc} file"
            )
            msg += " " if n_files_proc == 1 else "s "
            msg += (
                f"had analysis results added to {args.db_connection_str} "
                "(latest listed below)"
            )
        else:
            msg += f" and {n_msgs_proc} messages were successfully processed"
        msg += f" from {run_start} to {run_stop}"
        for fn in proc_filepaths:
            msg += f"\n\t{fn}"
        flyer_analysis.logger.info(msg)


def main(args=None):
    "Run the stream processor from the command line or given arguments"
    FlyerAnalysisStreamProcessor.run_from_command_line(args=args)


if __name__ == "__main__":
    main()
