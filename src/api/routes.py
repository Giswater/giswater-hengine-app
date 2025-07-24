"""
Routes for the Giswater Hydraulic Engine API.
Handles INP file uploads and management using PostgreSQL database.
"""
import os
import uuid
from datetime import datetime
from typing import List, Union
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlmodel import Session

from .models import (
    FileUploadResponse,
    AllInpFilesResponse,
    InpFileInfo,
    ErrorResponse
)
from .database import get_db_session, InpFileRepository

router = APIRouter(prefix="/inp", tags=["INP Files"])

# Configuration
UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".inp"}
MAX_FILE_SIZE = 250 * 1024 * 1024  # 250MB


def ensure_upload_dir():
    """Ensure upload directory exists"""
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)


def is_valid_inp_file(filename: str) -> bool:
    """Check if file has valid INP extension"""
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)


@router.post(
    "/upload",
    response_model=Union[FileUploadResponse, ErrorResponse],
    description="Upload an INP file for hydraulic modeling. Only .inp files are accepted."
)
async def upload_inp_file(
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session)
):
    """
    Upload an INP file to the server and store metadata in database.
    
    Args:
        file: The INP file to upload
        session: Database session
        
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
                message=f"Invalid file type. Only {ALLOWED_EXTENSIONS} files are allowed.",
                error_detail=f"File '{file.filename}' does not have a valid INP extension"
            )

        # Read file content to check size
        content = await file.read()
        file_size = len(content)

        # Check file size
        if file_size > MAX_FILE_SIZE:
            return ErrorResponse(
                status="Failed",
                message=f"File too large. Maximum size is {MAX_FILE_SIZE / 1024 / 1024}MB.",
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

        # Create file metadata for database
        upload_time = datetime.now()
        file_data = {
            "file_id": file_id,
            "filename": file.filename,
            "file_path": file_path,
            "file_size": file_size,
            "upload_time": upload_time
        }

        # Save to database
        try:
            db_file = InpFileRepository.create_file(session, file_data)
        except Exception as db_error:
            # If database save fails, remove the uploaded file
            if os.path.exists(file_path):
                os.remove(file_path)
            return ErrorResponse(
                status="Failed",
                message="Failed to save file metadata to database",
                error_detail=str(db_error)
            )

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
    description="Get all uploaded INP files with their metadata from database."
)
async def get_all_inp_files(session: Session = Depends(get_db_session)):
    """
    Retrieve information about all uploaded INP files from database.
    
    Args:
        session: Database session
    
    Returns:
        AllInpFilesResponse: List of all uploaded INP files
        ErrorResponse: Error response if retrieval fails
    """
    try:
        # Get all files from database
        db_files = InpFileRepository.get_all_files(session)

        # Convert to InpFileInfo objects and verify file existence
        files = []
        files_to_cleanup = []

        for db_file in db_files:
            # Check if file actually exists on disk
            if os.path.exists(db_file.file_path):
                files.append(InpFileInfo(
                    file_id=db_file.file_id,
                    filename=db_file.filename,
                    upload_time=db_file.upload_time,
                    file_size=db_file.file_size,
                    file_path=db_file.file_path
                ))
            else:
                # Mark for cleanup if file doesn't exist on disk
                files_to_cleanup.append(db_file.file_id)

        # Clean up database records for missing files
        for file_id in files_to_cleanup:
            InpFileRepository.delete_file(session, file_id)

        return AllInpFilesResponse(
            status="Accepted",
            message="Retrieved INP files successfully",
            total_files=len(files),
            files=files
        )

    except Exception as e:
        return ErrorResponse(
            status="Failed",
            message="Failed to retrieve INP files from database",
            error_detail=str(e)
        )


@router.get(
    "/files/{file_id}",
    response_model=Union[InpFileInfo, ErrorResponse],
    description="Get specific INP file metadata by file ID."
)
async def get_inp_file_by_id(
    file_id: str,
    session: Session = Depends(get_db_session)
):
    """
    Retrieve specific INP file information by file ID.
    
    Args:
        file_id: Unique file identifier
        session: Database session
    
    Returns:
        InpFileInfo: File information
        ErrorResponse: Error response if file not found
    """
    try:
        # Get file from database
        db_file = InpFileRepository.get_file_by_id(session, file_id)

        if not db_file:
            return ErrorResponse(
                status="Failed",
                message="File not found",
                error_detail=f"No file found with ID: {file_id}"
            )

        # Check if file exists on disk
        if not os.path.exists(db_file.file_path):
            # Clean up database record for missing file
            InpFileRepository.delete_file(session, file_id)
            return ErrorResponse(
                status="Failed",
                message="File not found on disk",
                error_detail=f"File {file_id} exists in database but not on disk"
            )

        return InpFileInfo(
            file_id=db_file.file_id,
            filename=db_file.filename,
            upload_time=db_file.upload_time,
            file_size=db_file.file_size,
            file_path=db_file.file_path
        )

    except Exception as e:
        return ErrorResponse(
            status="Failed",
            message="Failed to retrieve file information",
            error_detail=str(e)
        )


@router.delete(
    "/files/{file_id}",
    response_model=Union[dict, ErrorResponse],
    description="Delete an INP file and its metadata."
)
async def delete_inp_file(
    file_id: str,
    session: Session = Depends(get_db_session)
):
    """
    Delete an INP file from both disk and database.
    
    Args:
        file_id: Unique file identifier
        session: Database session
    
    Returns:
        dict: Success message
        ErrorResponse: Error response if deletion fails
    """
    try:
        # Get file info from database
        db_file = InpFileRepository.get_file_by_id(session, file_id)

        if not db_file:
            return ErrorResponse(
                status="Failed",
                message="File not found",
                error_detail=f"No file found with ID: {file_id}"
            )

        # Remove file from disk if it exists
        if os.path.exists(db_file.file_path):
            os.remove(db_file.file_path)

        # Remove from database
        success = InpFileRepository.delete_file(session, file_id)

        if success:
            return {
                "status": "Accepted",
                "message": "File deleted successfully",
                "file_id": file_id
            }
        else:
            return ErrorResponse(
                status="Failed",
                message="Failed to delete file from database",
                error_detail=f"Could not remove file {file_id} from database"
            )

    except Exception as e:
        return ErrorResponse(
            status="Failed",
            message="Failed to delete file",
            error_detail=str(e)
        )
