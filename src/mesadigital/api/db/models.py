from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


target_metadata = Base.metadata
