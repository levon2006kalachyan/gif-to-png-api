
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс моделей SQLAlchemy."""
    pass


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[int] = mapped_column(Integer, nullable=False)
    locale: Mapped[str] = mapped_column(String, default="", nullable=False)
    user_agent: Mapped[str] = mapped_column(String, default="", nullable=False)

    instructions: Mapped[list["InstructionModel"]] = relationship(
        back_populates="session_record"
    )


class InstructionModel(Base):
    __tablename__ = "instructions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[int] = mapped_column(Integer, nullable=False)
    argument: Mapped[str] = mapped_column(String, nullable=False)
    session: Mapped[int] = mapped_column(
        ForeignKey("sessions.id"), nullable=False
    )
    tags: Mapped[str] = mapped_column(String, default="", nullable=False)

    session_record: Mapped["SessionModel"] = relationship(
        back_populates="instructions"
    )
    completions: Mapped[list["CompletionModel"]] = relationship(
        back_populates="instruction_record"
    )


class CompletionModel(Base):
    __tablename__ = "completions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[str] = mapped_column(String, default="", nullable=False)
    stage: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    failure: Mapped[str] = mapped_column(String, default="", nullable=False)
    instruction: Mapped[int] = mapped_column(
        ForeignKey("instructions.id"), nullable=False
    )
    cache_hit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    instruction_record: Mapped["InstructionModel"] = relationship(
        back_populates="completions"
    )
