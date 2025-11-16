from typing import TypedDict, Dict, List, Any


class NumericStats(TypedDict):
    sum: float
    mean: float
    min: float
    max: float


class StringStats(TypedDict):
    unique_values_count: int
    unique_values: List[str]


class BasicAnalysis(TypedDict):
    numeric_columns: Dict[str, NumericStats]
    string_columns: Dict[str, StringStats]


class FileUploadResponse(TypedDict):
    table_data: List[Dict[str, Any]]
    columns: List[str]
    total_rows: int
    current_page: int
    page_size: int
    total_pages: int
    basic_analysis: BasicAnalysis


