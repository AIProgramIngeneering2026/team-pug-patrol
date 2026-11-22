from __future__ import annotations

from ..errors import FileNotFound, InvalidInput
from ..storage import FileNotInStorage, FileStorage, StoredFile

MAX_FILE_BYTES = 1_048_576


def load(storage: FileStorage, file_id: str, field: str) -> StoredFile:
    try:
        return storage.get(file_id)
    except FileNotInStorage:
        raise FileNotFound(f"file '{file_id}' not found", field=field) from None


def decode_utf8(stored: StoredFile, field: str) -> str:
    if len(stored.content) > MAX_FILE_BYTES:
        raise InvalidInput(field, f"file is larger than {MAX_FILE_BYTES} bytes")
    try:
        return stored.content.decode("utf-8")
    except UnicodeDecodeError:
        raise InvalidInput(field, "file is not valid UTF-8 text") from None


def extension(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""
