#imports
from sqlalchemy import Integer, String, Text, Double, Identity
from sqlalchemy.orm import mapped_column, Mapped
from .orm_base import ORMBase

class FlyerAnalysisEntry(ORMBase) :
    """
    A class describing entries in the flyer analysis table using sqlalchemy ORM
    """

    FLYER_ANALYSIS_TABLE_NAME='flyer_analysis_results'

    __tablename__ = FLYER_ANALYSIS_TABLE_NAME

    ID            = mapped_column(Integer,Identity(1,1),primary_key=True)   
    rel_filepath  = mapped_column(Text,unique=True,nullable=False)
    exit_code     = mapped_column(Integer,nullable=False)
    radius        = mapped_column(Double)
    tilt          = mapped_column(Double)
    leading_row   = mapped_column(Double)
    center_row    = mapped_column(Double)
    center_column = mapped_column(Double)

    def __init__(self,rel_filepath,exit_code,radius,tilt,leading_row,center_row,center_column) :
        self.rel_filepath = str(rel_filepath)
        self.exit_code = exit_code
        self.radius = radius
        self.tilt = tilt
        self.leading_row = leading_row
        self.center_row = center_row
        self.center_column = center_column
