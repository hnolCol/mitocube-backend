import pytest
from fastapi import HTTPException

from config.enums.users.roles import UserRolesEnum


def test_group_curator_sits_between_standard_and_curator():
    assert UserRolesEnum.STANDARD < UserRolesEnum.GROUP_CURATOR < UserRolesEnum.CURATOR
    assert UserRolesEnum.CURATOR < UserRolesEnum.ADMIN


class TestGroupCuratorMaintenancePermissions:
    """Group curators may edit the Experimental Metadata entities but must
    stay below the CURATOR threshold everywhere else."""

    THRESHOLDS = {
        "attributes": "src/routers/attributes/permissions.py",
        "genotypes": "src/routers/genotypes/permissions.py",
        "annotations": "src/routers/annotations/permissions.py",
    }

    def test_experimental_metadata_edit_threshold_is_group_curator(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        for name, rel in self.THRESHOLDS.items():
            content = (root / "src" / rel.split("src/")[-1]).read_text()
            assert "edit = user.role >= UserRolesEnum.GROUP_CURATOR" in content, name

    def test_instruments_stay_above_group_curator(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        content = (root / "src" / "routers" / "instruments" / "instruments.py").read_text()
        assert "user.role >= UserRolesEnum.CURATOR" in content
        assert "GROUP_CURATOR" not in content

    def test_research_group_and_consortium_creation_stay_above_group_curator(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        for rel in ["routers/researchgroups/researchgroup.py", "routers/consortiums/consortium.py"]:
            content = (root / "src" / rel).read_text()
            assert "GROUP_CURATOR" not in content, rel


class TestGroupCuratorUserCreation:
    """Group curators may only create users for their own research groups
    and never with a role above their own."""

    @pytest.fixture
    def route(self):
        from routers.authentication import user as user_router
        return user_router.add_user_to_the_database

    @staticmethod
    def _make_db(own_groups, all_groups):
        class FakeResearchGroups:
            def __init__(self):
                self.calls = []

            def find(self, user_tags=None, limit=None, **kwargs):
                self.calls.append(("find", user_tags))
                return list(own_groups)

            def exists(self, tag):
                return tag in all_groups

        class FakeDB:
            def __init__(self):
                self.research_groups = FakeResearchGroups()

        return FakeDB()

    def _make_user(self, role):
        import time
        from pydantic import SecretStr
        from config.models.user import UserModel

        return UserModel(
            tag="groupcur",
            firstname="Group",
            lastname="Curator",
            email="group.curator@age.mpg.de",
            created_at=time.time(),
            password=SecretStr("irrelevant"),
            role=role,
            allow_login=True,
        )

    def _make_props(self, groups, role=UserRolesEnum.STANDARD):
        from config.models.user import UserCreateModel

        return UserCreateModel(
            firstname="New",
            lastname="User",
            email="new.user@age.mpg.de",
            research_group_tags=groups,
            role=role,
        )

    def test_group_curator_cannot_create_user_for_foreign_group(self, route):
        from services.encryption import create_password_hash
        from pydantic import SecretStr
        import time

        user = self._make_user(UserRolesEnum.GROUP_CURATOR)
        db = self._make_db(own_groups={"grpown"}, all_groups={"grpown", "grpother"})
        props = self._make_props(groups=["grpother"])
        with pytest.raises(HTTPException) as e:
            route(background_task=None, user_props=props, user=user, db=db)
        assert e.value.status_code == 403

    def test_group_curator_cannot_assign_role_above_own(self, route):
        user = self._make_user(UserRolesEnum.GROUP_CURATOR)
        db = self._make_db(own_groups={"grpown"}, all_groups={"grpown"})
        props = self._make_props(groups=["grpown"], role=UserRolesEnum.CURATOR)
        with pytest.raises(HTTPException):
            route(background_task=None, user_props=props, user=user, db=db)

    def test_group_curator_can_create_user_for_own_group(self, route):
        user = self._make_user(UserRolesEnum.GROUP_CURATOR)
        db = self._make_db(own_groups={"grpown"}, all_groups={"grpown"})

        class FakeUsers:
            def get_new_tag(self):
                return "newusert"

            def create_plain_password(self):
                return "plain-password"

            def hash_password(self, pw):
                return "hashed"

            def insert(self, user_props):
                return True

        class FakeNews:
            def insert(self, _):
                return True

        db.users = FakeUsers()
        db.news = FakeNews()

        import routers.authentication.user as user_router_module

        original = user_router_module.send_email_in_background

        def fake_send(*args, **kwargs):
            return None

        user_router_module.send_email_in_background = fake_send
        try:
            props = self._make_props(groups=["grpown"])

            class FakeResearchGroupsInsert:
                def find(self, user_tags=None, limit=None, **kwargs):
                    return ["grpown"]

                def exists(self, tag):
                    return tag == "grpown"

                def insert_users(self, tag, user_tags):
                    return True

            db.research_groups = FakeResearchGroupsInsert()
            result = route(background_task=None, user_props=props, user=user, db=db)
            assert result is None
        finally:
            user_router_module.send_email_in_background = original

    def test_standard_user_rejected_by_route_gate(self, route):
        import inspect

        from services.users import is_user_at_least_group_curator

        sig = inspect.signature(route)
        assert sig.parameters["user"].default.dependency is is_user_at_least_group_curator
        with pytest.raises(HTTPException):
            is_user_at_least_group_curator(self._make_user(UserRolesEnum.STANDARD))


class TestScopedStateChangeGate:
    """The submission state-change routes accept global curators and group
    curators whose scope contains the submission, nobody else."""

    @staticmethod
    def _call(user, db):
        from services.users import is_curator_or_scoped_group_curator
        return is_curator_or_scoped_group_curator("subm-1", user, db)

    def _make_user(self, role):
        import time
        from pydantic import SecretStr
        from config.models.user import UserModel

        return UserModel(
            tag="groupcur", firstname="G", lastname="C",
            email="g.c@age.mpg.de", created_at=time.time(),
            password=SecretStr("x"), role=role, allow_login=True,
        )

    def _make_db(self, accessible):
        class FF:
            def has_user_access(self, user_tag, submission_tag):
                return submission_tag in accessible
        class DB:
            def __init__(self):
                self.submission_filter = FF()
        return DB()

    def test_global_curator_passes_regardless_of_scope(self):
        assert self._call(self._make_user(UserRolesEnum.CURATOR), self._make_db([])) is not None

    def test_group_curator_in_scope_passes(self):
        assert self._call(self._make_user(UserRolesEnum.GROUP_CURATOR), self._make_db(["subm-1"])) is not None

    def test_group_curator_out_of_scope_rejected(self):
        with pytest.raises(HTTPException):
            self._call(self._make_user(UserRolesEnum.GROUP_CURATOR), self._make_db([]))

    def test_standard_user_rejected(self):
        with pytest.raises(HTTPException):
            self._call(self._make_user(UserRolesEnum.STANDARD), self._make_db(["subm-1"]))

    def test_state_change_routes_use_scoped_gate(self):
        import inspect
        from routers.submission import submission as submission_router
        for fn in (submission_router.update_submission_state, submission_router.update_submission):
            dep = inspect.signature(fn).parameters["user"].default
            assert dep.dependency.__name__ == "is_curator_or_scoped_group_curator"
