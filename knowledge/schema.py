from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Union

class Figure(BaseModel):
    caption: str
    page: Union[int, str] = 0          # Allow both int and string
    description: str = ""

    @field_validator('page', mode='before')
    @classmethod
    def convert_page_to_int(cls, v):
        if isinstance(v, str):
            try:
                return int(v.strip())
            except ValueError:
                return 0
        return v


class Table(BaseModel):
    caption: str
    page: Union[int, str] = 0
    description: str = ""

    @field_validator('page', mode='before')
    @classmethod
    def convert_page_to_int(cls, v):
        if isinstance(v, str):
            try:
                return int(v.strip())
            except ValueError:
                return 0
        return v


class PaperKnowledge(BaseModel):
    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: str = ""
    sections: Dict[str, str] = Field(default_factory=dict)
    figures: List[Figure] = Field(default_factory=list)
    tables: List[Table] = Field(default_factory=list)
    metadata: Dict = Field(default_factory=dict)