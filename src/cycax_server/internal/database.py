from api.config import settings
from sqlmodel import Field, Session, SQLModel, create_engine

engine = create_engine(settings.DATABASE_URI, echo=True)


class Tasks(SQLModel, table=True):
    id: str | None = Field(default=None, primary_key=True)
    path: str
    state: str


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_db():
    with Session(engine) as session:
        yield session
