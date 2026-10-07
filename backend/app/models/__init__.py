from app.models.candidate import CandidateCategory, CandidateProfile, CandidateSkill, WorkFormat
from app.models.employer import EmployerProfile
from app.models.fsp import FSPAchievement, FSPProfile
from app.models.jobs import (
    Application,
    ApplicationStatus,
    AssignmentStatus,
    ContactAccessLog,
    Invitation,
    InvitationStatus,
    Job,
    JobSkill,
    MatchResult,
    ShortTask,
    SubmissionStatus,
    TaskAssignment,
    TaskAudience,
    TaskMode,
    TaskSubmission,
)
from app.models.reference import Competency, Grade, Skill, Specialization
from app.models.testing import (
    AttemptStatus,
    Question,
    QuestionType,
    TestAnswer,
    TestAttempt,
    TestItem,
    TestResult,
)
from app.models.user import Role, User

# Prevent pytest from trying to collect ORM classes whose names start with "Test".
for _cls in (TestAnswer, TestAttempt, TestItem, TestResult):
    _cls.__test__ = False

__all__ = [
    "Application",
    "ApplicationStatus",
    "AssignmentStatus",
    "AttemptStatus",
    "CandidateProfile",
    "CandidateCategory",
    "CandidateSkill",
    "Competency",
    "ContactAccessLog",
    "EmployerProfile",
    "FSPAchievement",
    "FSPProfile",
    "Grade",
    "Invitation",
    "InvitationStatus",
    "Job",
    "JobSkill",
    "MatchResult",
    "Question",
    "QuestionType",
    "Role",
    "ShortTask",
    "SubmissionStatus",
    "TaskAssignment",
    "TaskAudience",
    "TaskMode",
    "Skill",
    "Specialization",
    "TaskSubmission",
    "TestAnswer",
    "TestAttempt",
    "TestItem",
    "TestResult",
    "User",
    "WorkFormat",
]
