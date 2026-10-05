"""Reference data: specializations, grades, competencies (test blueprint) and the skill catalog."""

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Specialization(Base):
    __tablename__ = "specializations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # slug: backend, frontend...
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    competencies: Mapped[list["Competency"]] = relationship(
        back_populates="specialization", order_by="Competency.sort_order"
    )


class Grade(Base):
    __tablename__ = "grades"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # junior, middle, senior
    name: Mapped[str] = mapped_column(String(32))
    rank: Mapped[int] = mapped_column(Integer, unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    # Ability (theta) cut-point on the IRT scale that confirms the grade.
    theta_cut: Mapped[float] = mapped_column(Float)


class Competency(Base):
    """A measured competency of a specialization. `weight` is its share in the test blueprint."""

    __tablename__ = "competencies"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # be_db, fe_js...
    specialization_id: Mapped[str] = mapped_column(ForeignKey("specializations.id"), index=True)
    name: Mapped[str] = mapped_column(String(96))
    weight: Mapped[float] = mapped_column(Float)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    specialization: Mapped[Specialization] = relationship(back_populates="competencies")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(24), default="tool")  # language|framework|db|tool|practice
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    # Competencies whose test results confirm this skill: {"backend": "be_db", "data_ml": "ml_data"}
    competency_map: Mapped[dict] = mapped_column(JSON, default=dict)
    # Similar skills used for soft matching: {"flask": 0.7}
    related: Mapped[dict] = mapped_column(JSON, default=dict)
