"""Unit tests for Base model and TimestampMixin."""

import pytest
from datetime import datetime
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class TestModel(Base, TimestampMixin):
    """Test model that uses TimestampMixin."""

    __tablename__ = "test_models"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[int] = mapped_column(nullable=False)


class TestBaseModel:
    """Test cases for Base model."""

    def test_base_inheritance(self):
        """Test that Base is a valid DeclarativeBase."""
        assert hasattr(Base, "registry")
        assert hasattr(Base, "metadata")

    def test_base_can_create_models(self):
        """Test that Base can be used to create models."""
        # TestModel should inherit from Base
        assert issubclass(TestModel, Base)


class TestTimestampMixin:
    """Test cases for TimestampMixin."""

    @pytest.fixture
    def test_instance(self):
        """Create a test model instance."""
        return TestModel(id="test_1", name="Test Item", value=42)

    def test_mixin_adds_created_at(self, test_instance):
        """Test that TimestampMixin adds created_at field."""
        assert hasattr(test_instance, "created_at")

    def test_mixin_adds_updated_at(self, test_instance):
        """Test that TimestampMixin adds updated_at field."""
        assert hasattr(test_instance, "updated_at")

    def test_created_at_is_mapped(self):
        """Test that created_at is properly mapped."""
        assert "created_at" in TestModel.__table__.columns

    def test_updated_at_is_mapped(self):
        """Test that updated_at is properly mapped."""
        assert "updated_at" in TestModel.__table__.columns

    def test_repr_basic(self, test_instance):
        """Test __repr__ method with basic model."""
        repr_str = repr(test_instance)

        # Should contain class name
        assert "TestModel" in repr_str

        # Should contain all column values
        assert "id='test_1'" in repr_str
        assert "name='Test Item'" in repr_str
        assert "value=42" in repr_str

    def test_repr_with_special_characters(self):
        """Test __repr__ with special characters in values."""
        instance = TestModel(
            id="test_2",
            name="Test's \"Item\"",  # Contains apostrophe and quotes
            value=100,
        )

        repr_str = repr(instance)
        assert "TestModel" in repr_str
        assert "id='test_2'" in repr_str
        # Python's repr should escape the quotes properly
        assert "name=" in repr_str

    def test_repr_with_none_values(self):
        """Test __repr__ with columns that might be None."""
        # Create minimal instance
        instance = TestModel(id="test_3", name="Test", value=0)

        repr_str = repr(instance)
        assert "TestModel" in repr_str
        assert "id='test_3'" in repr_str
        assert "value=0" in repr_str

    def test_repr_includes_all_columns(self, test_instance):
        """Test that __repr__ includes all table columns."""
        repr_str = repr(test_instance)

        # Check all expected columns are mentioned
        column_names = [col.name for col in TestModel.__table__.columns]
        for col_name in column_names:
            assert col_name in repr_str

    def test_repr_format(self, test_instance):
        """Test __repr__ has correct format."""
        repr_str = repr(test_instance)

        # Should start with class name and opening paren
        assert repr_str.startswith("TestModel(")

        # Should end with closing paren
        assert repr_str.endswith(")")

        # Should contain comma-separated attributes
        assert ", " in repr_str

    def test_timestamp_columns_exist(self):
        """Test that timestamp columns exist in table."""
        assert "created_at" in TestModel.__table__.columns
        assert "updated_at" in TestModel.__table__.columns

    def test_created_at_not_nullable(self):
        """Test that created_at is not nullable."""
        created_col = TestModel.__table__.columns["created_at"]
        assert created_col.nullable is False

    def test_updated_at_not_nullable(self):
        """Test that updated_at is not nullable."""
        updated_col = TestModel.__table__.columns["updated_at"]
        assert updated_col.nullable is False

    def test_columns_have_server_defaults(self):
        """Test that timestamp columns have server defaults."""
        created_col = TestModel.__table__.columns["created_at"]
        updated_col = TestModel.__table__.columns["updated_at"]

        assert created_col.server_default is not None
        assert updated_col.server_default is not None

    def test_updated_at_has_onupdate(self):
        """Test that updated_at has onupdate set."""
        updated_col = TestModel.__table__.columns["updated_at"]
        assert updated_col.onupdate is not None

    def test_mixin_with_multiple_instances(self):
        """Test mixin works correctly with multiple instances."""
        instance1 = TestModel(id="test_a", name="First", value=1)
        instance2 = TestModel(id="test_b", name="Second", value=2)

        # Both should have timestamp fields
        assert hasattr(instance1, "created_at")
        assert hasattr(instance2, "created_at")

        # Their repr should be different
        repr1 = repr(instance1)
        repr2 = repr(instance2)
        assert repr1 != repr2

    def test_repr_with_numeric_values(self):
        """Test __repr__ with various numeric values."""
        instance = TestModel(id="test_nums", name="Numbers", value=-999)

        repr_str = repr(instance)
        assert "value=-999" in repr_str

    def test_repr_with_empty_string(self):
        """Test __repr__ with empty string value."""
        instance = TestModel(id="test_empty", name="", value=0)

        repr_str = repr(instance)
        assert "name=''" in repr_str or 'name=""' in repr_str
