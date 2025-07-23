"""
Routes for the Giswater Hydraulic Engine API.
Handles INP file uploads and management.
"""
import os
import json
import uuid
from datetime import datetime
from typing import List, Union
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from .models import (
    FileUploadResponse, 
    AllInpFilesResponse, 
    InpFileInfo, 
    ErrorResponse
)

router = APIRouter(prefix="/inp", tags=["INP Files"])

# Configuration
UPLOAD_DIR = "uploads"
METADATA_FILE = os.path.join(UPLOAD_DIR, "files_metadata.json")
ALLOWED_EXTENSIONS = {".inp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def ensure_upload_dir():
    """Ensure upload directory exists"""
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)


def load_metadata() -> List[dict]:
    """Load file metadata from JSON file"""
    ensure_upload_dir()
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_metadata(metadata: List[dict]):
    """Save file metadata to JSON file"""
    ensure_upload_dir()
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, default=str, indent=2)


def is_valid_inp_file(filename: str) -> bool:
    """Check if file has valid INP extension"""
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)


@router.post(
    "/upload",
    response_model=Union[FileUploadResponse, ErrorResponse],
    description="Upload an INP file for hydraulic modeling. Only .inp files are accepted."
)
async def upload_inp_file(file: UploadFile = File(...)):
    """
    Upload an INP file to the server.
    
    Args:
        file: The INP file to upload
        
    Returns:
        FileUploadResponse: Success response with file details
        ErrorResponse: Error response if upload fails
    """
    try:
        # Check if filename is provided
        if not file.filename:
            return ErrorResponse(
                status="Failed",
                message="No filename provided.",
                error_detail="Upload request must include a filename"
            )
        
        # Validate file extension
        if not is_valid_inp_file(file.filename):
            return ErrorResponse(
                status="Failed",
                message="Invalid file type. Only .inp files are allowed.",
                error_detail=f"File '{file.filename}' does not have a valid INP extension"
            )
        
        # Read file content to check size
        content = await file.read()
        file_size = len(content)
        
        # Check file size
        if file_size > MAX_FILE_SIZE:
            return ErrorResponse(
                status="Failed",
                message="File too large. Maximum size is 10MB.",
                error_detail=f"File size: {file_size} bytes, Max allowed: {MAX_FILE_SIZE} bytes"
            )
        
        # Check if file is empty
        if file_size == 0:
            return ErrorResponse(
                status="Failed",
                message="Empty file uploaded.",
                error_detail="File has no content"
            )
        
        # Generate unique file ID and create file path
        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        ensure_upload_dir()
        
        # Save file to disk
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Create file metadata
        upload_time = datetime.now()
        file_info = {
            "file_id": file_id,
            "filename": file.filename,
            "upload_time": upload_time.isoformat(),
            "file_size": file_size,
            "file_path": file_path
        }
        
        # Load existing metadata and add new file
        metadata = load_metadata()
        metadata.append(file_info)
        save_metadata(metadata)
        
        return FileUploadResponse(
            status="Accepted",
            message="File uploaded successfully",
            filename=file.filename,
            file_id=file_id,
            upload_time=upload_time,
            file_size=file_size
        )
        
    except Exception as e:
        return ErrorResponse(
            status="Failed",
            message="Failed to upload file",
            error_detail=str(e)
        )


@router.get(
    "/files",
    response_model=Union[AllInpFilesResponse, ErrorResponse],
    description="Get all uploaded INP files with their metadata."
)
async def get_all_inp_files():
    """
    Retrieve information about all uploaded INP files.
    
    Returns:
        AllInpFilesResponse: List of all uploaded INP files
        ErrorResponse: Error response if retrieval fails
    """
    try:
        # Load file metadata
        metadata = load_metadata()
        
        # Convert to InpFileInfo objects and filter existing files
        files = []
        valid_metadata = []
        
        for file_info in metadata:
            # Check if file actually exists on disk and has required fields
            file_path = file_info.get("file_path", "")
            filename = file_info.get("filename", "")
            
            if file_path and filename and os.path.exists(file_path):
                files.append(InpFileInfo(
                    file_id=file_info["file_id"],
                    filename=filename,
                    upload_time=datetime.fromisoformat(file_info["upload_time"]),
                    file_size=file_info["file_size"],
                    file_path=file_path
                ))
                valid_metadata.append(file_info)
        
        # Update metadata to remove references to deleted files
        if len(valid_metadata) != len(metadata):
            save_metadata(valid_metadata)
        
        return AllInpFilesResponse(
            status="Accepted",
            message="Retrieved INP files successfully",
            total_files=len(files),
            files=files
        )
        
    except Exception as e:
        return ErrorResponse(
            status="Failed",
            message="Failed to retrieve INP files",
            error_detail=str(e)
        )
