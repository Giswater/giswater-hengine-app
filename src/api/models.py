"""
Models for the giswater-hengine-app FastAPI application.
Follows similar patterns to the giswater-api for consistency.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class FileUploadResponse(BaseModel):
    """Response model for file upload endpoint"""
    status: Literal["Accepted", "Failed"] = Field(..., description="Status of the upload", examples=["Accepted"])
    message: str = Field(..., description="Response message", examples=["File uploaded successfully"])
    filename: str = Field(..., description="Name of the uploaded file", examples=["model.inp"])
    file_id: str = Field(..., description="Unique identifier for the uploaded file", examples=["file_123456"])
    upload_time: datetime = Field(..., description="Timestamp when the file was uploaded")
    file_size: int = Field(..., description="Size of the uploaded file in bytes", examples=[1024])


class InpFileInfo(BaseModel):
    """Model for individual INP file information"""
    file_id: str = Field(..., description="Unique identifier for the file", examples=["file_123456"])
    filename: str = Field(..., description="Original filename", examples=["model.inp"])
    upload_time: datetime = Field(..., description="Timestamp when the file was uploaded")
    file_size: int = Field(..., description="Size of the file in bytes", examples=[1024])
    file_path: str = Field(..., description="Relative path to the stored file", examples=["uploads/file_123456_model.inp"])


class AllInpFilesResponse(BaseModel):
    """Response model for getting all INP files"""
    status: Literal["Accepted", "Failed"] = Field(..., description="Status of the request", examples=["Accepted"])
    message: str = Field(..., description="Response message", examples=["Retrieved INP files successfully"])
    total_files: int = Field(..., description="Total number of INP files", examples=[5])
    files: List[InpFileInfo] = Field(..., description="List of all INP files")


class ErrorResponse(BaseModel):
    """Error response model"""
    status: Literal["Failed"] = Field(..., description="Status indicating failure", examples=["Failed"])
    message: str = Field(..., description="Error message", examples=["File upload failed"])
    error_detail: Optional[str] = Field(None, description="Detailed error information") 