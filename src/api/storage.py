
from dataclasses import asdict, dataclass
from threading import RLock
from time import time


@dataclass
class Session:
    id: int
    timestamp: int
    locale: str
    user_agent: str


@dataclass
class Instruction:
    id: int
    timestamp: int
    argument: str
    session: int
    tags: str


@dataclass
class Completion:
    id: int
    timestamp: int
    result: str
    stage: str
    failure: str
    instruction: int
    cache_hit: int
    duration: int


class MemoryStorage:
    """Потокобезопасное хранилище данных в памяти."""

    def __init__(self):
        self._lock = RLock()

        self.sessions = {}
        self.instructions = {}
        self.completions = {}

        self._next_session_id = 1
        self._next_instruction_id = 1
        self._next_completion_id = 1

    def add_session(self, locale="", user_agent=""):
        with self._lock:
            session = Session(
                id=self._next_session_id,
                timestamp=int(time()),
                locale=locale,
                user_agent=user_agent,
            )

            self.sessions[session.id] = session
            self._next_session_id += 1

            return asdict(session)

    def scan_sessions(self):
        with self._lock:
            return [
                asdict(session)
                for session in self.sessions.values()
            ]

    def get_session(self, session_id):
        with self._lock:
            session = self.sessions.get(session_id)

            if session is None:
                return None

            return asdict(session)

    def edit_session(self, session_id, **changes):
        with self._lock:
            session = self.sessions.get(session_id)

            if session is None:
                return None

            for field in ("locale", "user_agent"):
                if field in changes:
                    setattr(session, field, changes[field])

            return asdict(session)

    def add_instruction(self, session_id, argument, tags=""):
        with self._lock:
            if session_id not in self.sessions:
                raise ValueError("Session not found")

            instruction = Instruction(
                id=self._next_instruction_id,
                timestamp=int(time()),
                argument=argument,
                session=session_id,
                tags=tags,
            )

            self.instructions[instruction.id] = instruction
            self._next_instruction_id += 1

            return asdict(instruction)

    def scan_instructions(self, session_id):
        with self._lock:
            return [
                asdict(instruction)
                for instruction in self.instructions.values()
                if instruction.session == session_id
            ]

    def get_instruction(self, instruction_id):
        with self._lock:
            instruction = self.instructions.get(instruction_id)

            if instruction is None:
                return None

            return asdict(instruction)

    def edit_instruction(self, instruction_id, **changes):
        with self._lock:
            instruction = self.instructions.get(instruction_id)

            if instruction is None:
                return None

            for field in ("argument", "tags"):
                if field in changes:
                    setattr(instruction, field, changes[field])

            return asdict(instruction)

    def add_completion(
        self,
        instruction_id,
        result="",
        stage="pending",
        failure="",
        cache_hit=0,
        duration=0,
    ):
        with self._lock:
            if instruction_id not in self.instructions:
                raise ValueError("Instruction not found")

            completion = Completion(
                id=self._next_completion_id,
                timestamp=int(time()),
                result=result,
                stage=stage,
                failure=failure,
                instruction=instruction_id,
                cache_hit=cache_hit,
                duration=duration,
            )

            self.completions[completion.id] = completion
            self._next_completion_id += 1

            return asdict(completion)

    def scan_completions(self, instruction_id):
        with self._lock:
            return [
                asdict(completion)
                for completion in self.completions.values()
                if completion.instruction == instruction_id
            ]

    def get_completion(self, completion_id):
        with self._lock:
            completion = self.completions.get(completion_id)

            if completion is None:
                return None

            return asdict(completion)

    def edit_completion(self, completion_id, **changes):
        with self._lock:
            completion = self.completions.get(completion_id)

            if completion is None:
                return None

            for field in (
                "result",
                "stage",
                "failure",
                "cache_hit",
                "duration",
            ):
                if field in changes:
                    setattr(completion, field, changes[field])

            return asdict(completion)

    def report_scan(self):
        """Отчёт по завершённым задачам за последние 6 минут."""

        with self._lock:
            cutoff = int(time()) - 360

            report = []

            for completion in self.completions.values():
                instruction = self.instructions.get(
                    completion.instruction
                )

                if instruction is None:
                    continue

                if instruction.timestamp < cutoff:
                    continue

                report.append({
                    "duration": completion.duration,
                    "result": completion.result,
                    "tags": instruction.tags,
                })

            return report
