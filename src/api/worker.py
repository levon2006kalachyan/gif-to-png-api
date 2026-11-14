
import subprocess
import sys
import threading
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"


class ConversionWorker:
    """Выполняет GIF → PNG в фоновом потоке через subprocess."""

    def __init__(self, storage, test_mode=False):
        self.storage = storage
        self.test_mode = test_mode

    def start(self, instruction):
        """Создаёт Completion и запускает фоновую задачу."""

        completion = self.storage.add_completion(
            instruction_id=instruction["id"],
            stage="pending",
        )

        thread = threading.Thread(
            target=self._execute,
            args=(instruction, completion["id"]),
            daemon=True,
        )
        thread.start()

        return completion

    def _execute(self, instruction, completion_id):
        started = time.monotonic()

        self.storage.edit_completion(
            completion_id,
            stage="running",
        )

        try:
            if self.test_mode:
                result_path = f"test-output/{instruction['id']}.png"
            else:
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

                input_path = Path(instruction["argument"])

                if not input_path.is_absolute():
                    input_path = PROJECT_ROOT / input_path

                output_path = (
                    OUTPUT_DIR
                    / f"instruction_{instruction['id']}"
                      f"_completion_{completion_id}.png"
                )

                input_data = (
                    f"{input_path}\n{output_path}\n"
                )

                process = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "src.converter",
                    ],
                    input=input_data,
                    text=True,
                    capture_output=True,
                    cwd=PROJECT_ROOT,
                    timeout=60,
                    check=False,
                )

                if process.returncode != 0:
                    raise RuntimeError(
                        process.stderr.strip()
                        or "Conversion failed"
                    )

                if not output_path.is_file():
                    raise RuntimeError(
                        "PNG output file was not created"
                    )

                result_path = str(output_path)

            duration = int(
                (time.monotonic() - started) * 1000
            )

            self.storage.edit_completion(
                completion_id,
                stage="completed",
                result=result_path,
                failure="",
                duration=duration,
            )

        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            duration = int(
                (time.monotonic() - started) * 1000
            )

            self.storage.edit_completion(
                completion_id,
                stage="failed",
                failure=str(error),
                duration=duration,
            )
