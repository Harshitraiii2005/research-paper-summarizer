from pydantic import BaseModel, Field
from typing import List, Dict

class Figure(BaseModel):
    caption: str
    page: int
    description: str = ""

class Table(BaseModel):
    caption: str
    page: int
    description: str = ""

class PaperKnowledge(BaseModel):
    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: str = ""
    sections: Dict[str, str] = Field(default_factory=dict)
    figures: List[Figure] = Field(default_factory=list)
    tables: List[Table] = Field(default_factory=list)
    metadata: Dict = Field(default_factory=dict)