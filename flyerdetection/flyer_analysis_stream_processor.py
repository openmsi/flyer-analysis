# imports
import datetime, threading
from io import BytesIO
import numpy as np, pandas as pd
from PIL import Image
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, scoped_session
from openmsistream import DataFileStreamProcessor
from .orm_base import ORMBase
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
        drop_existing=False,
        verbose=False,
        **other_kwargs,
    ):
        super().__init__(config_file, topic_name, **other_kwargs)
        # either create an engine to interact with a DB, or store the path to the output file
        self._engine = None
        self._output_file = None
        analysis_table_name = FlyerAnalysisEntry.FLYER_ANALYSIS_TABLE_NAME
        image_table_name = FlyerImageEntry.FLYER_IMAGE_TABLE_NAME
        if db_connection_str is not None:
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
            if drop_existing:
                self.logger.info(
                    f"Dropping and recreating the {analysis_table_name} table"
                )
                self.__drop_existing_tables()
                self.__create_tables()
            inspector = inspect(self._engine)
            for table_name in (analysis_table_name, image_table_name):
                if not inspector.has_table(table_name):
                    self.__create_tables()
                    break
        else:
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

    def __drop_existing_tables(self):
        """
        Drop the table in the database
        """
        ORMBase.metadata.drop_all(
            bind=self._engine,
            tables=[FlyerAnalysisEntry.__table__, FlyerImageEntry.__table__],
        )

    def __create_tables(self):
        """
        Create the table in the database
        """
        ORMBase.metadata.create_all(
            bind=self._engine,
            tables=[FlyerAnalysisEntry.__table__, FlyerImageEntry.__table__],
        )

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

    def __write_result_to_DB(self, result, img_bytestring, lock):
        """
        Write a given result to the output database
        """
        analysis_entry = FlyerAnalysisEntry(
            result.rel_filepath,
            result.exit_code,
            result.radius,
            result.tilt,
            result.leading_row,
            result.center_row,
            result.center_column,
        )
        if result.analysis_image is None:
            analysis_img_bytestring = None
        else:
            mem_stream = BytesIO()
            np.savez_compressed(mem_stream, result.analysis_image)
            mem_stream.seek(0)
            analysis_img_bytestring = mem_stream.read()
        thread_id = threading.get_ident()
        if thread_id not in self._sessions_by_thread_ident:
            with lock:
                self._sessions_by_thread_ident[thread_id] = self._scoped_session()
        self._sessions_by_thread_ident[thread_id].add(analysis_entry)
        self._sessions_by_thread_ident[thread_id].commit()
        image_entry = FlyerImageEntry(
            analysis_entry.ID,
            img_bytestring,
            analysis_img_bytestring,
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
                "(SQLAlchemy format). Output will go in a .csv file if "
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
