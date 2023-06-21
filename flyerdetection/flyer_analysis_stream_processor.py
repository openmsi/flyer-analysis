# imports
import datetime, threading, os, getpass
from io import BytesIO
import numpy as np, pandas as pd
from PIL import Image
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, scoped_session
import fmrest
from openmsistream import DataFileStreamProcessor
from .orm_base import ORMBase
from .video_metadata_entry import VideoMetadataEntry
from .flyer_analysis_entry import FlyerAnalysisEntry
from .flyer_image_entry import FlyerImageEntry
from .flyer_detection import Flyer_Detection, flyer_characteristics


class FlyerAnalysisStreamProcessor(DataFileStreamProcessor):
    """
    A class to run flyer analysis for all .bmp images in a topic
    and add their results to an output file or database

    The original .bmp image and the analysis result image will be
    stored in a secondary table if output is going to a DB
    """

    def __init__(
        self,
        config_file,
        topic_name,
        *,
        db_connection_str=None,
        filemaker_url=None,
        drop_existing=False,
        verbose=False,
        **other_kwargs,
    ):
        super().__init__(config_file, topic_name, **other_kwargs)
        # either create an engine to interact with a DB, with a FileMaker DB connection,
        # or store the path to the output file
        self._engine = None
        self._filemaker_server = None
        self._output_file = None
        analysis_table_name = FlyerAnalysisEntry.FLYER_ANALYSIS_TABLE_NAME
        if db_connection_str is not None:
            # connect to the filemaker server
            self._filemaker_server = self.__get_filemaker_server(filemaker_url)
            # if a connection string was given, connect to the DB
            try:
                self._engine = create_engine(db_connection_str, echo=verbose)
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
            for table_name in [table.name for table in self.__get_all_tables()]:
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
            result = None
            analyzer = Flyer_Detection()
            img = np.asarray(Image.open(BytesIO(datafile.bytestring)))
            # filtering the image sometimes fails, use a special exit code in this case
            try:
                filtered_image = analyzer.filter_image(img)
            except Exception as exc:
                result = flyer_characteristics()
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
                self.__write_result_to_DB(result, datafile.bytestring, lock)
        except Exception as exc:
            return exc
        return None

    def _on_shutdown(self):
        super()._on_shutdown()
        self._engine.dispose()

    def __get_filemaker_uname_and_pword(self):
        """
        Get the FileMaker username and password from environment variables or user input
        """
        uname_env_var = "FILEMAKER_UNAME"
        username = os.path.expandvars(f"${uname_env_var}")
        if username==f"${uname_env_var}" :
            username = (input('Please enter your JHED username: ')).rstrip()
        pword_env_var = "FILEMAKER_PWORD"
        password = os.path.expandvars(f"${pword_env_var}")
        if password==f"${pword_env_var}" :
            password = getpass.getpass(f"Please enter the JHED password for {username}: ")
        return username, password
    
    def __get_filemaker_server(self,filemaker_url):
        """
        Create a FileMaker REST API server connection to the "Experiment" layout
        and return it
        """
        username = None
        password = None
        try:
            username, password = self.__get_filemaker_uname_and_pword()
            fms = fmrest.Server(
                filemaker_url,
                user=username,
                password=password,
                database="Laser Shock",
                layout="Experiment",
                verify_ssl=False,
                api_version="v1",
            )
            fms.login()
            return fms
        except Exception as exc:
            warnmsg = (
                "WARNING: failed to authenticate to the FileMaker metadata DB "
                f"(username: {username}, password given?: {'yes' if password else 'no'}). "
                "Video metadata entries will not be added to the output DB. "
                "Exception traceback will be logged."
            )
            self.logger.warning(warnmsg,exc_info=exc)
            return None

    def __get_all_tables(self):
        """
        Return a list of all relevant table objects
        """
        all_tables = [
            FlyerAnalysisEntry.__table__,
            FlyerImageEntry.__table__,
        ]
        if self._filemaker_server:
            all_tables.append(VideoMetadataEntry.__table__)
        return all_tables

    def __drop_existing_tables(self):
        """
        Drop the table in the database
        """
        ORMBase.metadata.drop_all(bind=self._engine,tables=self.__get_all_tables())

    def __create_tables(self):
        """
        Create the table in the database
        """
        ORMBase.metadata.create_all(bind=self._engine,tables=self.__get_all_tables())

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

    def __get_video_metadata_ID_for_frame(self,result,lock,session):
        """
        Return the ID of a metadata record created for the video associated with a given
        result for a frame. Creates the record if necessary
        """
        pass
    
    def __write_result_to_DB(self, result, img_bytestring, lock):
        """
        Write a given result to the output database
        """
        # figure out the session to use
        thread_id = threading.get_ident()
        if thread_id not in self._sessions_by_thread_ident:
            with lock:
                self._sessions_by_thread_ident[thread_id] = self._scoped_session()
        # get the ID of the video metadata entry for this frame, adding it if necessary
        video_metadata_ID = self.__get_video_metadata_ID_for_frame()
        # add the analysis result entry
        analysis_entry = FlyerAnalysisEntry.from_ID_and_result(video_metadata_ID,result)
        self._sessions_by_thread_ident[thread_id].add(analysis_entry)
        self._sessions_by_thread_ident[thread_id].commit()
        # add the image entry
        image_entry = FlyerImageEntry.from_ID_img_and_result(analysis_entry.ID,img_bytestring,result)
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
            "--filemaker_url",
            help=(
                "The URL of the FileMaker server to connect to for fetching video metadata. "
                "If this isn't given (or the filemaker username/password can't be determined "
                "from environment variables or user input) then no entries will be added to "
                "the video metadata table. Only relevant with a db_connection_str given."
            )
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
            filemaker_url=args.filemaker_url,
            drop_existing=args.drop_existing,
            verbose=args.verbose,
            output_dir=args.output_dir,
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
    FlyerAnalysisStreamProcessor.run_from_command_line(args=args)


if __name__ == "__main__":
    main()
