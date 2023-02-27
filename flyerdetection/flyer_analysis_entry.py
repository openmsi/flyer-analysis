#imports
from sqlalchemy import Integer, String, Text, Double, Numeric, Identity, SmallInteger
from sqlalchemy.orm import mapped_column, Mapped
from .orm_base import ORMBase

class FlyerAnalysisEntry(ORMBase) :
    """
    A class describing entries in the flyer analysis table using sqlalchemy ORM
    """

    FLYER_ANALYSIS_TABLE_NAME='flyer_analysis_results'

    __tablename__ = FLYER_ANALYSIS_TABLE_NAME

    ID            = mapped_column(Integer,primary_key=True)   
    rel_filepath  = mapped_column(String(896),unique=True,nullable=False)
    exit_code     = mapped_column(SmallInteger,nullable=False)
    radius        = mapped_column(Numeric)
    tilt          = mapped_column(Numeric)
    leading_row   = mapped_column(SmallInteger)
    center_row    = mapped_column(Numeric)
    center_column = mapped_column(Numeric)

    def __init__(self,rel_filepath,exit_code,radius,tilt,leading_row,center_row,center_column) :
        self.rel_filepath = str(rel_filepath)
        self.exit_code = int(exit_code)
        self.radius = float(radius)
        self.tilt = float(tilt)
        self.leading_row = int(leading_row)
        self.center_row = float(center_row)
        self.center_column = float(center_column)
