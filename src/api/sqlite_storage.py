from pathlib import Path
from time import time

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from src.api.models import (
    Base,
    CompletionModel,
    InstructionModel,
    SessionModel,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "gif_to_png.db"


class SQLiteStorage:
    """Постоянное хранилище SQLite на основе SQLAlchemy."""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = DEFAULT_DB_PATH

        db_path = Path(db_path).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(
            f"sqlite:///{db_path.as_posix()}",
            connect_args={"timeout": 30},
        )

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, connection_record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(self.engine)

        self.SessionFactory = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )

    @staticmethod
    def _session_dict(obj):
        return {
            "id": obj.id,
            "timestamp": obj.timestamp,
            "locale": obj.locale,
            "user_agent": obj.user_agent,
        }

    @staticmethod
    def _instruction_dict(obj):
        return {
            "id": obj.id,
            "timestamp": obj.timestamp,
            "argument": obj.argument,
            "session": obj.session,
            "tags": obj.tags,
        }

    @staticmethod
    def _completion_dict(obj):
        return {
            "id": obj.id,
            "timestamp": obj.timestamp,
            "result": obj.result,
            "stage": obj.stage,
            "failure": obj.failure,
            "instruction": obj.instruction,
            "cache_hit": obj.cache_hit,
            "duration": obj.duration,
        }

    def add_session(self, locale="", user_agent=""):
        with self.SessionFactory.begin() as db:
            obj = SessionModel(
                timestamp=int(time()),
                locale=locale,
                user_agent=user_agent,
            )
            db.add(obj)
            db.flush()
            return self._session_dict(obj)

    def scan_sessions(self):
        with self.SessionFactory() as db:
            objects = db.scalars(
                select(SessionModel).order_by(SessionModel.id)
            ).all()
            return [self._session_dict(obj) for obj in objects]

    def get_session(self, session_id):
        with self.SessionFactory() as db:
            obj = db.get(SessionModel, session_id)
            return None if obj is None else self._session_dict(obj)

    def edit_session(self, session_id, **changes):
        with self.SessionFactory.begin() as db:
            obj = db.get(SessionModel, session_id)

            if obj is None:
                return None

            for field in ("locale", "user_agent"):
                if field in changes:
                    setattr(obj, field, changes[field])

            db.flush()
            return self._session_dict(obj)

    def add_instruction(self, session_id, argument, tags=""):
        with self.SessionFactory.begin() as db:
            if db.get(SessionModel, session_id) is None:
                raise ValueError("Session not found")

            obj = InstructionModel(
                timestamp=int(time()),
                argument=argument,
                session=session_id,
                tags=tags,
            )
            db.add(obj)
            db.flush()
            return self._instruction_dict(obj)

    def scan_instructions(self, session_id):
        with self.SessionFactory() as db:
            objects = db.scalars(
                select(InstructionModel)
                .where(InstructionModel.session == session_id)
                .order_by(InstructionModel.id)
            ).all()
            return [self._instruction_dict(obj) for obj in objects]

    def get_instruction(self, instruction_id):
        with self.SessionFactory() as db:
            obj = db.get(InstructionModel, instruction_id)
            return None if obj is None else self._instruction_dict(obj)

    def edit_instruction(self, instruction_id, **changes):
        with self.SessionFactory.begin() as db:
            obj = db.get(InstructionModel, instruction_id)

            if obj is None:
                return None

            for field in ("argument", "tags"):
                if field in changes:
                    setattr(obj, field, changes[field])

            db.flush()
            return self._instruction_dict(obj)

    def add_completion(
        self,
        instruction_id,
        result="",
        stage="pending",
        failure="",
        cache_hit=0,
        duration=0,
    ):
        with self.SessionFactory.begin() as db:
            if db.get(InstructionModel, instruction_id) is None:
                raise ValueError("Instruction not found")

            obj = CompletionModel(
                timestamp=int(time()),
                result=result,
                stage=stage,
                failure=failure,
                instruction=instruction_id,
                cache_hit=cache_hit,
                duration=duration,
            )
            db.add(obj)
            db.flush()
            return self._completion_dict(obj)

    def scan_completions(self, instruction_id):
        with self.SessionFactory() as db:
            objects = db.scalars(
                select(CompletionModel)
                .where(CompletionModel.instruction == instruction_id)
                .order_by(CompletionModel.id)
            ).all()
            return [self._completion_dict(obj) for obj in objects]

    def get_completion(self, completion_id):
        with self.SessionFactory() as db:
            obj = db.get(CompletionModel, completion_id)
            return None if obj is None else self._completion_dict(obj)

    def edit_completion(self, completion_id, **changes):
        with self.SessionFactory.begin() as db:
            obj = db.get(CompletionModel, completion_id)

            if obj is None:
                return None

            for field in (
                "result",
                "stage",
                "failure",
                "cache_hit",
                "duration",
            ):
                if field in changes:
                    setattr(obj, field, changes[field])

            db.flush()
            return self._completion_dict(obj)

    def report_scan(self):
        """Отчёт по инструкциям за последние 6 минут."""

        cutoff = int(time()) - 360

        with self.SessionFactory() as db:
            rows = db.execute(
                select(
                    CompletionModel.duration,
                    CompletionModel.result,
                    InstructionModel.tags,
                )
                .join(
                    InstructionModel,
                    CompletionModel.instruction == InstructionModel.id,
                )
                .where(InstructionModel.timestamp >= cutoff)
                .order_by(CompletionModel.id)
            ).all()

            return [
                {
                    "duration": duration,
                    "result": result,
                    "tags": tags,
                }
                for duration, result, tags in rows
            ]

    def close(self):
        """Освобождает соединения с базой данных."""
        self.engine.dispose()
