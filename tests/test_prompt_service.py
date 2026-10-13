import pytest

from core.database import init_db
from schemas.prompt import PromptCreate, PromptUpdate
from services import prompt_service
from services.prompt_service import PromptNotFoundError, PromptNameExistsError, DefaultPromptDeletionError

VALID_CONTENT = "Tu es un analyste. Résume le diagramme UML en 5 lignes."


def make_prompt(name="Résumé court", content=VALID_CONTENT, description="Version courte"):
    return prompt_service.create_prompt(PromptCreate(name=name, description=description, content=content))


# --- Database initialisation -------------------------------------------------

def test_init_db_creates_one_default_prompt(temp_db, default_prompt_name):
    prompts = prompt_service.list_prompts()
    assert len(prompts) == 1
    assert prompts[0]["name"] == default_prompt_name
    assert prompts[0]["is_default"] is True


def test_init_db_twice_does_not_duplicate_default_prompt(temp_db):
    init_db()
    assert len(prompt_service.list_prompts()) == 1


# --- Nominal cases -----------------------------------------------------------

def test_create_prompt_returns_saved_prompt(temp_db):
    prompt = make_prompt(name="  Résumé court  ")
    assert prompt["id"] > 0
    assert prompt["name"] == "Résumé court"  # name is trimmed
    assert prompt["is_default"] is False
    assert prompt["created_at"] and prompt["updated_at"]


def test_list_prompts_returns_default_first_then_alphabetical(temp_db, default_prompt_name):
    make_prompt(name="Zèbre prompt")
    make_prompt(name="Alpha prompt")
    names = [p["name"] for p in prompt_service.list_prompts()]
    assert names == [default_prompt_name, "Alpha prompt", "Zèbre prompt"]


def test_get_prompt_returns_the_right_prompt(temp_db):
    created = make_prompt()
    assert prompt_service.get_prompt(created["id"])["name"] == "Résumé court"


def test_get_default_prompt_returns_the_default(temp_db, default_prompt_name):
    assert prompt_service.get_default_prompt()["name"] == default_prompt_name


def test_update_prompt_changes_fields(temp_db):
    created = make_prompt()
    updated = prompt_service.update_prompt(
        created["id"], PromptUpdate(name="Résumé très court", description=None, content=VALID_CONTENT + " 3 lignes.")
    )
    assert updated["name"] == "Résumé très court"
    assert updated["description"] is None
    assert updated["content"].endswith("3 lignes.")


def test_update_prompt_can_keep_its_own_name(temp_db):
    created = make_prompt()
    updated = prompt_service.update_prompt(created["id"], PromptUpdate(name="Résumé court", content=VALID_CONTENT))
    assert updated["name"] == "Résumé court"


def test_delete_prompt_removes_it(temp_db):
    created = make_prompt()
    prompt_service.delete_prompt(created["id"])
    with pytest.raises(PromptNotFoundError):
        prompt_service.get_prompt(created["id"])


def test_set_default_prompt_keeps_exactly_one_default(temp_db):
    created = make_prompt()
    prompt_service.set_default_prompt(created["id"])
    defaults = [p for p in prompt_service.list_prompts() if p["is_default"]]
    assert [p["id"] for p in defaults] == [created["id"]]


# --- Complex case ------------------------------------------------------------

def test_full_scenario_new_default_then_delete_old_default(temp_db):
    old_default = prompt_service.get_default_prompt()
    new_prompt = make_prompt()

    with pytest.raises(DefaultPromptDeletionError):
        prompt_service.delete_prompt(old_default["id"])

    prompt_service.set_default_prompt(new_prompt["id"])
    prompt_service.delete_prompt(old_default["id"])

    remaining = prompt_service.list_prompts()
    assert len(remaining) == 1
    assert remaining[0]["id"] == new_prompt["id"] and remaining[0]["is_default"] is True


# --- Error cases -------------------------------------------------------------

def test_get_prompt_unknown_id_raises_not_found(temp_db):
    with pytest.raises(PromptNotFoundError):
        prompt_service.get_prompt(999)


def test_get_default_prompt_returns_none_when_table_is_empty(temp_db):
    # Only possible if the table was emptied manually
    from core.database import get_connection
    with get_connection() as conn:
        conn.execute("DELETE FROM prompts")
    assert prompt_service.get_default_prompt() is None


def test_create_prompt_with_existing_name_raises_conflict(temp_db):
    make_prompt()
    with pytest.raises(PromptNameExistsError):
        make_prompt()


def test_update_prompt_to_existing_name_raises_conflict(temp_db, default_prompt_name):
    created = make_prompt()
    with pytest.raises(PromptNameExistsError):
        prompt_service.update_prompt(created["id"], PromptUpdate(name=default_prompt_name, content=VALID_CONTENT))


def test_update_unknown_prompt_raises_not_found(temp_db):
    with pytest.raises(PromptNotFoundError):
        prompt_service.update_prompt(999, PromptUpdate(name="Inconnu", content=VALID_CONTENT))


def test_delete_default_prompt_is_refused(temp_db):
    default = prompt_service.get_default_prompt()
    with pytest.raises(DefaultPromptDeletionError):
        prompt_service.delete_prompt(default["id"])


def test_delete_unknown_prompt_raises_not_found(temp_db):
    with pytest.raises(PromptNotFoundError):
        prompt_service.delete_prompt(999)


def test_set_default_unknown_prompt_raises_not_found(temp_db):
    with pytest.raises(PromptNotFoundError):
        prompt_service.set_default_prompt(999)
