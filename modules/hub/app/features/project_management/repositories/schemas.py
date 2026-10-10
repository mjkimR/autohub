from typing import Literal

from pydantic import BaseModel, Field


class RepoItemRead(BaseModel):
    name: str = Field(description="Item name")
    path: str = Field(description="Relative path within the repository")
    type: Literal["file", "dir"] = Field(description="Item kind: file or dir")
    size: int = Field(default=0, description="Size in bytes for files")
    sha: str = Field(default="", description="Git blob/tree SHA")


class RepoTreeRead(BaseModel):
    path: str = Field(default="", description="Current directory path")
    ref: str = Field(description="Branch, tag, or commit reference")
    items: list[RepoItemRead] = Field(default_factory=list, description="Items contained in the directory")


class RepoBlobRead(BaseModel):
    path: str = Field(description="File path within the repository")
    ref: str = Field(description="Branch, tag, or commit reference")
    size: int = Field(description="Size in bytes")
    sha: str = Field(description="Git blob SHA")
    encoding: Literal["utf-8", "base64"] = Field(default="utf-8", description="Encoding of the content field")
    content: str = Field(description="File content (decoded utf-8 or base64)")


class RepoInfoRead(BaseModel):
    repository: str = Field(description="Full repository name: owner/repo")
    default_branch: str = Field(description="Repository default branch name")
    branches: list[str] = Field(default_factory=list, description="Available branch names")
