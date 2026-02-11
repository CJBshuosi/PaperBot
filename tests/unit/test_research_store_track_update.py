from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from paperbot.infrastructure.stores.research_store import SqlAlchemyResearchStore


def test_update_track_name_success(tmp_path):
    """Test updating track name successfully."""
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyResearchStore(db_url=db_url, auto_create_schema=True)

    # Create a track
    track = store.create_track(user_id="test", name="Original Name", activate=False)
    track_id = track["id"]

    # Update the name
    updated = store.update_track(user_id="test", track_id=track_id, name="New Name")

    assert updated is not None
    assert updated["name"] == "New Name"
    assert updated["id"] == track_id


def test_update_track_description_success(tmp_path):
    """Test updating track description successfully."""
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyResearchStore(db_url=db_url, auto_create_schema=True)

    track = store.create_track(
        user_id="test", name="Test Track", description="Original", activate=False
    )
    track_id = track["id"]

    updated = store.update_track(
        user_id="test", track_id=track_id, description="Updated description"
    )

    assert updated is not None
    assert updated["description"] == "Updated description"


def test_update_track_keywords_success(tmp_path):
    """Test updating track keywords successfully."""
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyResearchStore(db_url=db_url, auto_create_schema=True)

    track = store.create_track(
        user_id="test", name="Test Track", keywords=["ml", "ai"], activate=False
    )
    track_id = track["id"]

    updated = store.update_track(
        user_id="test", track_id=track_id, keywords=["nlp", "transformers", "llm"]
    )

    assert updated is not None
    assert updated["keywords"] == ["nlp", "transformers", "llm"]


def test_update_track_multiple_fields(tmp_path):
    """Test updating multiple fields at once."""
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyResearchStore(db_url=db_url, auto_create_schema=True)

    track = store.create_track(
        user_id="test",
        name="Original",
        description="Original desc",
        keywords=["old"],
        venues=["venue1"],
        methods=["method1"],
        activate=False,
    )
    track_id = track["id"]

    updated = store.update_track(
        user_id="test",
        track_id=track_id,
        name="Updated",
        description="New desc",
        keywords=["new", "keywords"],
        venues=["venue2", "venue3"],
        methods=["method2"],
    )

    assert updated is not None
    assert updated["name"] == "Updated"
    assert updated["description"] == "New desc"
    assert updated["keywords"] == ["new", "keywords"]
    assert updated["venues"] == ["venue2", "venue3"]
    assert updated["methods"] == ["method2"]


def test_update_track_not_found(tmp_path):
    """Test updating non-existent track returns None."""
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyResearchStore(db_url=db_url, auto_create_schema=True)

    result = store.update_track(user_id="test", track_id=99999, name="Test")
    assert result is None


def test_update_track_duplicate_name_raises_integrity_error(tmp_path):
    """Test updating to duplicate name raises IntegrityError."""
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyResearchStore(db_url=db_url, auto_create_schema=True)

    # Create two tracks
    store.create_track(user_id="test", name="Track A", activate=False)
    track_b = store.create_track(user_id="test", name="Track B", activate=False)

    # Try to rename Track B to Track A
    with pytest.raises(IntegrityError):
        store.update_track(user_id="test", track_id=track_b["id"], name="Track A")


def test_update_track_preserves_other_fields(tmp_path):
    """Test that updating one field preserves other fields."""
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyResearchStore(db_url=db_url, auto_create_schema=True)

    track = store.create_track(
        user_id="test",
        name="Original",
        description="Original desc",
        keywords=["keyword1"],
        activate=False,
    )
    track_id = track["id"]

    # Update only the name
    updated = store.update_track(user_id="test", track_id=track_id, name="New Name")

    assert updated is not None
    assert updated["name"] == "New Name"
    # Other fields should remain unchanged
    assert updated["description"] == "Original desc"
    assert updated["keywords"] == ["keyword1"]


def test_update_track_wrong_user_returns_none(tmp_path):
    """Test that updating with wrong user_id returns None."""
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyResearchStore(db_url=db_url, auto_create_schema=True)

    track = store.create_track(user_id="user1", name="Test Track", activate=False)
    track_id = track["id"]

    # Try to update with different user
    result = store.update_track(user_id="user2", track_id=track_id, name="New Name")
    assert result is None


def test_update_track_updates_timestamp(tmp_path):
    """Test that updating track updates the updated_at timestamp."""
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyResearchStore(db_url=db_url, auto_create_schema=True)

    track = store.create_track(user_id="test", name="Test Track", activate=False)
    track_id = track["id"]
    original_updated_at = track["updated_at"]

    # Update the track
    updated = store.update_track(user_id="test", track_id=track_id, name="New Name")

    assert updated is not None
    assert updated["updated_at"] is not None
    # Updated timestamp should be different (or equal if very fast)
    assert updated["updated_at"] >= original_updated_at
