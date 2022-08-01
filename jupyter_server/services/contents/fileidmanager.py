import os
import sqlite3
import uuid
from typing import Optional, Tuple, Union

from jupyter_core.paths import jupyter_data_dir
from traitlets import Unicode
from traitlets.config.configurable import LoggingConfigurable


def new_uuid() -> str:
    return uuid.uuid4().hex


class FileIdManager(LoggingConfigurable):
    db_path = Unicode(
        default_value=os.path.join(jupyter_data_dir(), "file_id_manager.db"),
        help=(
            "The path of the DB file used by `FileIdManager`. "
            "Defaults to `jupyter_data_dir()/file_id_manager.db`."
        ),
        config=True,
    )

    def __init__(self, *args, **kwargs):
        # pass args and kwargs to parent Configurable
        super().__init__(**kwargs)
        # initialize connection with db
        self.con = sqlite3.connect(self.db_path)
        self.con.create_function("new_uuid", 0, new_uuid)
        self.log.debug("Creating File ID tables and indices")
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS Files(id BLOB PRIMARY KEY, path TEXT NOT NULL UNIQUE)"
        )
        self.con.execute("CREATE INDEX IF NOT EXISTS ix_Files_path ON FILES (path)")
        self.con.commit()

    def _normalize_path(self, path):
        """Normalizes a given file path."""
        path = os.path.normcase(path)
        path = os.path.normpath(path)
        return path

    def index(self, path: str) -> str:
        """Adds the file path to the Files table, then returns the file ID. If
        the file is already indexed, the file ID is immediately returned."""
        path = self._normalize_path(path)

        existing_id = self.get_id(path)
        if existing_id is not None:
            return existing_id

        fid_str = self._index(path)
        self.con.commit()
        return fid_str

    def _index(self, path: str) -> str:

        fid = uuid.uuid4()
        self._insert(
            "INSERT INTO Files (id, path) VALUES (?,?)",
            (
                fid.hex,
                path,
            ),
        )
        return str(fid)

    def insert(self, path: str, fid: Union[str, uuid.UUID, None] = None) -> str:
        """Adds the file path to the Files table, then returns the file ID. If
        the file is already indexed, the file ID is immediately returned."""
        path = self._normalize_path(path)

        if not fid:
            fid = uuid.uuid4()
        elif isinstance(fid, str):
            fid = uuid.UUID(fid)
        elif not isinstance(fid, uuid.UUID):
            raise ValueError("id must be a valid UUID")

        self._insert(
            "INSERT INTO Files (id, path) VALUES (?,?)",
            (
                fid.hex,
                path,
            ),
        )
        self.con.commit()
        return str(fid)

    def _insert(self, insert_stmt: str, values: Tuple) -> None:
        self.con.execute(insert_stmt, values)

    def get_id(self, path: str) -> Optional[str]:
        """Retrieves the file ID associated with a file path. Returns None if
        the file path has not yet been indexed."""
        path = self._normalize_path(path)
        row = self.con.execute("SELECT id FROM Files WHERE path = ?", (path,)).fetchone()
        return str(uuid.UUID(row[0])) if row else None

    def get_path(self, fid: str) -> Optional[str]:
        """Retrieves the file path associated with a file ID. Returns None if
        the ID does not exist in the Files table."""
        row = self.con.execute(
            "SELECT path FROM Files WHERE id = ?", (uuid.UUID(fid).hex,)
        ).fetchone()
        return row[0] if row else None

    def move(self, old_path, new_path, recursive=False):
        """Handles file moves by updating the file path of the associated file
        ID.  Returns the file ID."""
        old_path = self._normalize_path(old_path)
        new_path = self._normalize_path(new_path)
        self.log.debug(f"Moving file from ${old_path} to ${new_path}")

        if recursive:
            old_path_glob = os.path.join(old_path, "*")
            self.con.execute(
                "UPDATE Files SET path = ? || substr(path, ?) WHERE path GLOB ?",
                (new_path, len(old_path) + 1, old_path_glob),
            )

        fid = self.get_id(old_path)
        if fid is None:
            fid_uuid = uuid.uuid4()
            self._insert(
                "INSERT INTO Files (id, path) VALUES (?,?)",
                (
                    fid_uuid.hex,
                    new_path,
                ),
            )
            fid = str(fid_uuid)
        else:
            self.con.execute(
                "UPDATE Files SET path = ? WHERE id = ?", (new_path, uuid.UUID(fid).hex)
            )

        self.con.commit()
        return fid

    def copy(self, from_path, to_path, recursive=False):
        """Handles file copies by creating a new record in the Files table.
        Returns the file ID associated with `new_path`. Also indexes `old_path`
        if record does not exist in Files table. TODO: emit to event bus to
        inform client extensions to copy records associated with old file ID to
        the new file ID."""
        from_path = self._normalize_path(from_path)
        to_path = self._normalize_path(to_path)
        self.log.debug(f"Copying file from ${from_path} to ${to_path}")

        if recursive:
            from_path_glob = os.path.join(from_path, "*")
            self.con.execute(
                "INSERT INTO Files (id, path) SELECT new_uuid(), (? || substr(path, ?)) FROM Files WHERE path GLOB ?",
                (to_path, len(from_path) + 1, from_path_glob),
            )

        self.index(from_path)
        ret = self._index(to_path)
        self.con.commit()
        return ret

    def delete(self, path, recursive=False):
        """Handles file deletions by deleting the associated record in the File
        table. Returns None."""
        path = self._normalize_path(path)
        self.log.debug(f"Deleting file {path}")

        if recursive:
            path_glob = os.path.join(path, "*")
            self.con.execute("DELETE FROM Files WHERE path GLOB ?", (path_glob,))

        self.con.execute("DELETE FROM Files WHERE path = ?", (path,))
        self.con.commit()

    def _cleanup(self):
        """Cleans up `FileIdManager` by committing any pending transactions and
        closing the connection."""
        self.con.commit()
        self.con.close()
