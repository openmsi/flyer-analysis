"""Single ORM Base class for the flyer analysis tables in the database"""
# imports
from sqlalchemy.orm import DeclarativeBase


class ORMBase(DeclarativeBase):
    """
    A base class to use for defining ORM classes
    """
