# imports
from sqlalchemy import Integer, VARBINARY, ForeignKey
from sqlalchemy.orm import mapped_column, relationship
from .orm_base import ORMBase
from .flyer_analysis_entry import FlyerAnalysisEntry


class FlyerImageEntry(ORMBase):
    """
    A class describing entries in the flyer image table using sqlalchemy ORM
    """

    FLYER_IMAGE_TABLE_NAME = "flyer_images"

    __tablename__ = FLYER_IMAGE_TABLE_NAME

    ID = mapped_column(Integer, primary_key=True)
    analysis_result_ID = mapped_column(
        ForeignKey(f"{FlyerAnalysisEntry.FLYER_ANALYSIS_TABLE_NAME}.ID")
    )
    camera_image = mapped_column(VARBINARY(250000))
    analysis_image = mapped_column(VARBINARY(150000))

    rel_filepath = relationship(
        "FlyerAnalysisEntry", foreign_keys="FlyerImageEntry.analysis_result_ID"
    )

    def __init__(self, analysis_result_id, camera_image, analysis_image):
        self.analysis_result_ID = analysis_result_id
        self.camera_image = camera_image
        self.analysis_image = analysis_image
