from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base

# Use a dedicated Postgres schema for all tables to avoid polluting `public`.
# This sets the default schema for Table objects created via the declarative Base.
metadata = MetaData(schema="mailer")

Base = declarative_base(metadata=metadata)

