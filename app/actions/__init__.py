from msflib.account.actions import AccountAction, ProfileAction
from msflib.actions.base import ModelAction
from msflib.tenancy import TenantAction
from msflib.workspaces.actions import UserAction, WorkspaceAction

from ..core.config import settings
from ..models import (
    Account,
    AccountCreate,
    AccountUpdate,
    CharacterSample,
    CharacterSampleCreate,
    CharacterSampleUpdate,
    Document,
    DocumentCreate,
    DocumentUpdate,
    HandwritingProfile,
    HandwritingProfileCreate,
    HandwritingProfileUpdate,
    Profile,
    ProfileCreate,
    ProfileUpdate,
    Tenant,
    TenantCreate,
    TenantUpdate,
    User,
    UserCreate,
    UserUpdate,
    Workspace,
    WorkspaceCreate,
    WorkspaceUpdate,
)

tenant_action = TenantAction[Tenant, TenantCreate, TenantUpdate]()

account_action = AccountAction[Account, AccountCreate, AccountUpdate](settings=settings)

profile_action = ProfileAction[Profile, ProfileCreate, ProfileUpdate]()

workspace_action = WorkspaceAction[Workspace, WorkspaceCreate, WorkspaceUpdate](settings=settings)

user_action = UserAction[User, UserCreate, UserUpdate]()

handwriting_profile_action = ModelAction[
    HandwritingProfile, HandwritingProfileCreate, HandwritingProfileUpdate
]()

character_sample_action = ModelAction[
    CharacterSample, CharacterSampleCreate, CharacterSampleUpdate
]()

document_action = ModelAction[
    Document, DocumentCreate, DocumentUpdate
]()



