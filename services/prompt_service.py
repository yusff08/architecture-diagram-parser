import sqlite3
from typing import Optional
from core.database import get_connection
from schemas.prompt import PromptCreate, PromptUpdate


class PromptNotFoundError(Exception):
    pass

class PromptNameExistsError(Exception):
    pass

class DefaultPromptDeletionError(Exception):
    pass


def _to_dict(row: sqlite3.Row) -> dict:
    prompt = dict(row)
    prompt["is_default"] = bool(prompt["is_default"])
    return prompt


def list_prompts() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM prompts ORDER BY is_default DESC, name ASC").fetchall()
    return [_to_dict(row) for row in rows]


def get_prompt(prompt_id: int) -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
    if row is None:
        raise PromptNotFoundError(f"Prompt {prompt_id} introuvable.")
    return _to_dict(row)


def get_default_prompt() -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM prompts WHERE is_default = 1").fetchone()
    return _to_dict(row) if row else None


def create_prompt(data: PromptCreate) -> dict:
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO prompts (name, description, content) VALUES (?, ?, ?)",
                (data.name.strip(), data.description, data.content)
            )
            new_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        raise PromptNameExistsError(f"Un prompt nommé '{data.name}' existe déjà.")
    return get_prompt(new_id)


def update_prompt(prompt_id: int, data: PromptUpdate) -> dict:
    get_prompt(prompt_id)  # raises PromptNotFoundError
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE prompts SET name = ?, description = ?, content = ?, updated_at = datetime('now') WHERE id = ?",
                (data.name.strip(), data.description, data.content, prompt_id)
            )
    except sqlite3.IntegrityError:
        raise PromptNameExistsError(f"Un prompt nommé '{data.name}' existe déjà.")
    return get_prompt(prompt_id)


def delete_prompt(prompt_id: int):
    prompt = get_prompt(prompt_id)
    if prompt["is_default"]:
        raise DefaultPromptDeletionError("Impossible de supprimer le prompt par défaut. Définissez d'abord un autre prompt par défaut.")
    with get_connection() as conn:
        conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))


def set_default_prompt(prompt_id: int) -> dict:
    get_prompt(prompt_id)
    with get_connection() as conn:
        conn.execute("UPDATE prompts SET is_default = 0 WHERE is_default = 1")
        conn.execute("UPDATE prompts SET is_default = 1 WHERE id = ?", (prompt_id,))
    return get_prompt(prompt_id)
