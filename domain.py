from typing import List, Optional
from dns import rrset
from pydantic import (
    BaseModel,
    validator
)
import tldextract
import re


class Domain(BaseModel):
    name: str
    answer: List[Optional[rrset.RRset]]
    outcome: str
    popularity: int

    class Config:
        arbitrary_types_allowed = True

    @validator('name')
    def test_domain_name(cls, v) -> bool:
        """Domain name validator that rejects values with invalid TLD or not being matched by a generic domain regex"""
        v = v.strip().lower()
        cls.tld = str(tldextract.extract(v).suffix)
        regex = r"^((?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,6}$"
        p = re.compile(regex)
        if cls.tld == "":
            raise ValueError("Unable to determine TLD")
        if not(re.search(p, v)):
            raise ValueError("Invalid domain")
        return v
