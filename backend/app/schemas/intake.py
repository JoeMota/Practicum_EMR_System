from datetime import date, datetime
from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.schemas.common import APIModel


class StrictModel(APIModel):
    model_config = APIModel.model_config | ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def strip_whitespace(cls, value):
        return value.strip() if isinstance(value, str) else value


class IntakeCondition(StrictModel):
    name: str = Field(default="", max_length=80)
    year: str = Field(default="", pattern=r"^((19|20)\d{2})?$")


class IntakeSurgery(StrictModel):
    procedure: str = Field(default="", max_length=120)
    year: str = Field(default="", pattern=r"^((19|20)\d{2})?$")


class IntakeAllergy(StrictModel):
    agent: str = Field(default="", max_length=80)
    reaction: str = Field(default="", max_length=120)


class IntakeMedication(StrictModel):
    name: str = Field(default="", max_length=80)
    dose: str = Field(default="", max_length=60)
    frequency: str = Field(default="", max_length=60)


class IntakeRelative(StrictModel):
    relative: Literal["Mother", "Father", "Sibling", "Grandparent", "Child", "Other"]
    status: Literal["", "Living", "Deceased", "Unknown"] = ""
    conditions: str = Field(default="", max_length=200)


class IntakeData(StrictModel):
    preferred_name: str = Field(default="", max_length=100)
    pronouns: str = Field(default="", max_length=40)
    gender_identity: Literal["", "Woman", "Man", "Non-binary", "Another", "Prefer not to say"] = ""
    race: list[Literal[
        "American Indian or Alaska Native", "Asian", "Black or African American",
        "Native Hawaiian or Other Pacific Islander", "White", "Another race", "Prefer not to say",
    ]] = Field(default_factory=list, max_length=7)
    ethnicity: Literal["", "Hispanic or Latino", "Not Hispanic or Latino", "Prefer not to say"] = ""
    marital_status: Literal["", "Single", "Married", "Partnered", "Divorced", "Separated", "Widowed"] = ""
    interpreter_needed: bool = False
    email: str = Field(default="", max_length=120, pattern=r"^([^@\s]+@[^@\s]+\.[^@\s]+)?$")
    phone: str = Field(default="", max_length=40, pattern=r"^[0-9()+\-.\s]{0,40}$")
    phone_type: Literal["", "Mobile", "Home", "Work"] = ""
    address: str = Field(default="", max_length=300)
    city: str = Field(default="", max_length=80)
    state: str = Field(default="", pattern=r"^([A-Za-z]{2})?$")
    zip_code: str = Field(default="", pattern=r"^(\d{5}(-\d{4})?)?$")
    preferred_language: str = Field(default="", max_length=60)
    past_medical_history: str = Field(default="", max_length=4000)
    surgical_history: str = Field(default="", max_length=4000)
    family_history: str = Field(default="", max_length=4000)
    social_history: str = Field(default="", max_length=4000)
    insurance_payer: str = Field(default="", max_length=120)
    insurance_member_id: str = Field(default="", max_length=60)
    insurance_group_number: str = Field(default="", max_length=60)
    insurance_plan_type: Literal["", "HMO", "PPO", "EPO", "POS", "Medicare", "Medicaid", "Other"] = ""
    insurance_subscriber_is_patient: bool = True
    insurance_subscriber_name: str = Field(default="", max_length=120)
    insurance_subscriber_dob: date | None = None
    insurance_relationship: Literal["", "Self", "Spouse", "Child", "Other"] = ""
    insurance_effective_date: date | None = None
    secondary_insurance_payer: str = Field(default="", max_length=120)
    secondary_insurance_member_id: str = Field(default="", max_length=60)
    secondary_insurance_group_number: str = Field(default="", max_length=60)
    secondary_insurance_relationship: Literal["", "Self", "Spouse", "Child", "Other"] = ""
    conditions: list[IntakeCondition] = Field(default_factory=list, max_length=30)
    surgeries: list[IntakeSurgery] = Field(default_factory=list, max_length=20)
    allergies: list[IntakeAllergy] = Field(default_factory=list, max_length=20)
    no_known_allergies: bool = False
    medications: list[IntakeMedication] = Field(default_factory=list, max_length=25)
    family_members: list[IntakeRelative] = Field(default_factory=list, max_length=15)
    tobacco_use: Literal["", "Never", "Former", "Current"] = ""
    tobacco_detail: str = Field(default="", max_length=120)
    alcohol_use: Literal["", "None", "Occasional", "Weekly", "Daily"] = ""
    alcohol_detail: str = Field(default="", max_length=120)
    drug_use: Literal["", "Never", "Former", "Current"] = ""
    occupation: str = Field(default="", max_length=100)
    lives_with: str = Field(default="", max_length=100)
    exercise: str = Field(default="", max_length=120)
    emergency_contact_name: str = Field(default="", max_length=120)
    emergency_contact_phone: str = Field(default="", max_length=40)
    emergency_contact_relationship: str = Field(default="", max_length=60)
    preferred_pharmacy: str = Field(default="", max_length=160)
    confirmed_accurate: bool = False

    @field_validator("insurance_subscriber_dob", "insurance_effective_date", mode="before")
    @classmethod
    def empty_date_as_none(cls, value):
        return None if value == "" else value

    @model_validator(mode="after")
    def enforce_serialized_size_limit(self):
        if len(self.model_dump_json()) > 32_000:
            raise ValueError("Intake is too large.")
        return self


class IntakeIdentity(APIModel):
    first_name: str
    last_name: str
    dob: date
    sex_at_birth: str
    mrn: str


class PortalIntakeOut(APIModel):
    data: IntakeData
    identity: IntakeIdentity
    source: Literal["chart", "patient"]
    updated_at: datetime | None = None
    editable: bool
    not_editable_reason: str | None = None


class StaffIntakeOut(APIModel):
    submitted: bool
    data: IntakeData | None = None
    updated_at: datetime | None = None
