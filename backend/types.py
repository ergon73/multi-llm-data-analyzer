from typing import TypedDict, Dict, List, Any, Optional, Union


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
    dataset_id: str


class LLMAnalysisRequest(TypedDict):
    provider: str  # 'openai' | 'yandex' | 'giga'
    model: str
    table_data: List[Dict[str, Any]]


class LLMAnalysisResponse(TypedDict):
    model: str
    analysis: str
    timestamp: str


class ReportRequest(TypedDict):
    report_html: str


class FillMissingRequest(TypedDict):
    table_data: List[Dict[str, Any]]
    columns: List[str]
    missing_info: Dict[str, List[int]]  # column -> list of row indices


class FillRecommendation(TypedDict):
    row_idx: int
    suggested: Optional[Union[str, int, float]]
    confidence: float
    explanation: str


class FillMissingResponse(TypedDict):
    recommendations: Dict[str, List[FillRecommendation]]  # column -> list of recommendations


class UploadPageRequest(TypedDict):
    dataset_id: str
    page: int
    page_size: int


class UploadPageResponse(TypedDict):
    table_data: List[Dict[str, Any]]
    columns: List[str]
    total_rows: int
    current_page: int
    page_size: int
    total_pages: int
    dataset_id: str
    basic_analysis: BasicAnalysis


class TestResponse(TypedDict):
    status: str
    message: str
    timestamp: str
    version: str


