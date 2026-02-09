"""
# Step 3: Pydantic schema (schemas.py)

- Import `BaseModel` and `Field` from pydantic, and `List` from typing.
- Define **Citation** with:
  - `source_id: str` (required)
  - `quote: str` (required)
- Define **QAResponse** with:
  - `answer: str` (required)
  - `citations: List[Citation]` (default empty list)
- Use `Field(..., description="...")` for better docs and validation messages.
"""

# Step 3.1: Imports
# BaseModel – base class for your schemas
# Field – add metadata (required, default, description) to fields
# List – generic type for lists
from pydantic import BaseModel, Field
from typing import List


# Step 3.2: Citation model
# Add the Citation model:
class Citation(BaseModel):
    source_id: str = Field(..., description="ID of the source chunk or document")
    quote: str = Field(..., description="Exact short quote from the source")

# ... (Ellipsis) – field is required
# description – used for docs and some error messages
# Each citation has a source_id and a quote

# Step 3.3: QAResponse model

class QAResponse(BaseModel):
    answer: str = Field(..., description="Natural language answer to the question")
    citations: List[Citation] = Field(
        default_factory=list,
        description="List of citations that support the answer",
    )

# answer – required string
# citations – list of Citation objects
# default_factory=list – default empty list (don't use default=[])
# List[Citation] – a list of Citation objects


# quick validation test

if __name__ == "__main__":
    # Test validation
    data = {
        "answer": "Revenue was $50M, up 15% YoY.",
        "citations": [
            {"source_id": "doc_001", "quote": "revenue of $50M in Q3, up 15% YoY"}
        ],
    }
    result = QAResponse.model_validate(data)
    print(result.model_dump())
