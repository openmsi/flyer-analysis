# imports
from io import BytesIO
import numpy as np
from sqlalchemy import Integer, VARBINARY, ForeignKey
from sqlalchemy.orm import mapped_column, relationship
from .orm_base import ORMBase
from .flyer_analysis_entry import FlyerAnalysisEntry


class FlyerImageEntry(ORMBase):
    """
    A class describing entries in the flyer image table using sqlalchemy ORM
    """

    __tablename__ = "flyer_images"

    ID = mapped_column(Integer, primary_key=True)
    analysis_result_ID = mapped_column(
        ForeignKey(f"{FlyerAnalysisEntry.__tablename__}.ID")
    )
    camera_image = mapped_column(VARBINARY(250000))
    analysis_image = mapped_column(VARBINARY(150000))

    flyer_analysis_relation = relationship(
        "FlyerAnalysisEntry", foreign_keys="FlyerImageEntry.analysis_result_ID"
    )

    def __init__(self, analysis_result_id, camera_image, analysis_image):
        self.analysis_result_ID = analysis_result_id
        self.camera_image = camera_image
        self.analysis_image = analysis_image

    @classmethod
    def from_ID_img_and_result(cls, analysis_result_ID, img_bytestring, result):
        """
        Given the ID of an associated analysis result entry, the bytestring of
        the original .bmp image, and the "flyer_characteristics" result object
        from the flyer detection code, return a newly-created entry for the table
        """
        if result.analysis_image is None:
            analysis_img_bytestring = None
        else:
            mem_stream = BytesIO()
            np.savez_compressed(mem_stream, result.analysis_image)
            mem_stream.seek(0)
            analysis_img_bytestring = mem_stream.read()
        return cls(
            analysis_result_ID,
            img_bytestring,
            analysis_img_bytestring,
        )
