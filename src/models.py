from pydantic import BaseModel, Field
from typing import Optional, List, TypedDict

class WorkExperience(BaseModel):
    title: str = Field(..., description="Job title or role")
    company: str = Field(..., description="Company name")
    duration: str = Field(..., description="Duration of employment (e.g., 'June 2024 - July 2024')")
    description: str = Field(..., description="Details of responsibilities and achievements")

class Project(BaseModel):
    title: str = Field(..., description="Project title")
    desc: str = Field(..., description="Brief (10-15 words) description of the project")
    image: str = Field(..., description="Path or URL to project image")
    livelink: Optional[str] = Field(None, description="Live demo or deployment link (can be 'none')")
    repolink: Optional[str] = Field(None, description="GitHub or repository link (can be 'none')")

class SkillCategory(BaseModel):
    category: str = Field(..., description="Skill category name (e.g., 'Languages', 'Frameworks')")
    skills: List[str] = Field(..., description="List of skills under this category")

class SocialLink(BaseModel):
    url: str = Field(..., description="Full URL to social profile or resume")
    name: str = Field(..., description="Name of the platform (e.g., 'github', 'linkedin', 'resume')")

class Portfolio(BaseModel):
    name: str = Field(..., description="Full name of the user")
    mail: str = Field(..., description="Email address")
    resumeLink: str = Field(..., description="Link to the resume PDF or document")
    aboutme: str = Field(..., description="Personal introduction or bio")
    workExperience: List[WorkExperience] = Field(..., description="List of professional experiences")
    projects: List[Project] = Field(..., description="List of projects with metadata")
    skillsData: List[SkillCategory] = Field(..., description="List of categorized skills")
    socials: List[SocialLink] = Field(..., description="List of social or resume links")
    seoKeywords: List[str] = Field(..., description="List of SEO-relevant keywords for better visibility")
    pdfLinks: Optional[List[str]] = None


class AgentState(TypedDict):
    pdf_content: str
    pdf_bytes: Optional[bytes]
    extracted_data: Optional[Portfolio]
    pdf_links: Optional[List[str]]
    error: Optional[str]
    status: str