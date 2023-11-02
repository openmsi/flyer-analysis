"""ORM for a row in the metadata links table"""
# imports
import re, datetime
from sqlalchemy import Integer, DateTime, String
from sqlalchemy.orm import mapped_column
from .orm_base import ORMBase

# Regexes for parsing relative filepaths for metadata links
TC_FILENAME_REGEX = re.compile(r"^TC--20\d{2}(0\d|1[0-2])([0-2]\d|3[0-1])--\d{5}.bmp$")
HS_TAG_REGEX = re.compile(r"^HS--20\d{2}(0\d|1[0-2])([0-2]\d|3[0-1])--\d{5}$")
DATESTAMP_REGEX = re.compile(r"^20\d{2}_(0\d|1[0-2])_([0-2]\d|3[0-1])$")
CAMERA_FILENAME_REGEX = re.compile(r"^Camera_([0-1]\d|2[0-3])_[0-5]\d_[0-5]\d$")


class MetadataLinkEntry(ORMBase):
    """
    A class describing entries in a table with info to correlate individual videos
    with metadata from the FileMaker DB
    """

    __tablename__ = "metadata_links"

    ID = mapped_column(Integer, primary_key=True)
    datestamp = mapped_column(DateTime)
    experiment_day_counter = mapped_column(Integer)
    camera_filename = mapped_column(String)

    def __init__(self, datestamp, experiment_day_counter, camera_filename):
        super().__init__()
        self.datestamp = datestamp
        self.experiment_day_counter = experiment_day_counter
        self.camera_filename = camera_filename

    @staticmethod
    def get_link_fields_from_relative_filepath(rel_filepath):
        """
        Given a relative filepath for a particular frame .bmp file, return the
        values for the fields in its corresponding MetadataLinkEntry
        """
        rdict = {
            "datestamp": None,
            "experiment_day_counter": None,
            "camera_filename": None,
        }
        # check if the filename matches the "TC--*" pattern
        if TC_FILENAME_REGEX.match(rel_filepath.name):
            date_str = rel_filepath.name.split("--")[1]
            rdict["datestamp"] = datetime.datetime.strptime(date_str, "%Y%m%d")
            rdict["experiment_day_counter"] = int(
                rel_filepath.name[: -len(".bmp")].split("--")[-1]
            )
        parts = rel_filepath.parts
        # look for exactly one thing in the path like "HS--(datestamp)--(counter)"
        hs_parts = [part for part in parts if HS_TAG_REGEX.match(part)]
        if len(hs_parts) == 1:
            date_str = hs_parts[0].split("--")[1]
            rdict["datestamp"] = datetime.datetime.strptime(date_str, "%Y%m%d")
            rdict["experiment_day_counter"] = int(hs_parts[0].split("--")[-1])
        # next look for exactly one thing in the path like "yyyy_mm_dd"
        datestamp_parts = [part for part in parts if DATESTAMP_REGEX.match(part)]
        if len(datestamp_parts) == 1:
            rdict["datestamp"] = datetime.datetime.strptime(
                datestamp_parts[0], "%Y_%m_%d"
            )
        # finally, look for exactly one thing in the path like "Camera_hh_mm_ss"
        camera_filename_parts = [
            part for part in parts if CAMERA_FILENAME_REGEX.match(part)
        ]
        if len(camera_filename_parts) == 1:
            rdict["camera_filename"] = "_".join(camera_filename_parts[0].split("_")[1:])
        # return whatever we've found
        return rdict
