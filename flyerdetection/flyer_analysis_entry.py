# imports
from sqlalchemy import Integer, String, Float, SmallInteger, ForeignKey
from sqlalchemy.orm import mapped_column, relationship
from .orm_base import ORMBase
from .video_metadata_entry import VideoMetadataEntry


class FlyerAnalysisEntry(ORMBase):
    """
    A class describing entries in the flyer analysis table using sqlalchemy ORM
    """

    __tablename__ = "flyer_analysis_results"

    ID = mapped_column(Integer, primary_key=True)
    video_metadata_ID = mapped_column(
        ForeignKey(f"{VideoMetadataEntry.__tablename__}.ID")
    )
    rel_filepath = mapped_column(String(896), unique=True, nullable=False)
    exit_code = mapped_column(SmallInteger, nullable=False)
    radius = mapped_column(Float)
    tilt = mapped_column(Float)
    leading_row = mapped_column(SmallInteger)
    center_row = mapped_column(Float)
    center_column = mapped_column(Float)

    video_metadata_relation = relationship(
        "VideoMetadataEntry", foreign_keys="FlyerAnalysisEntry.video_metadata_ID"
    )

    def __init__(
        self,
        video_metadata_ID,
        rel_filepath,
        exit_code,
        radius,
        tilt,
        leading_row,
        center_row,
        center_column,
    ):
        self.video_metadata_ID = video_metadata_ID
        self.rel_filepath = str(rel_filepath) if rel_filepath else None
        self.exit_code = int(exit_code) if exit_code else None
        self.radius = float(radius) if radius else None
        self.tilt = float(tilt) if tilt else None
        self.leading_row = int(leading_row) if leading_row else None
        self.center_row = float(center_row) if center_row else None
        self.center_column = float(center_column) if center_column else None

    @classmethod
    def from_ID_and_result(cls,video_metadata_ID,result):
        """
        Given the ID of an associated video metadata entry and a "flyer_characteristics"
        result object from the flyer detection code, return a newly-created entry
        for the table
        """
        return cls(
            video_metadata_ID,
            result.rel_filepath,
            result.exit_code,
            result.radius,
            result.tilt,
            result.leading_row,
            result.center_row,
            result.center_column,
        )
