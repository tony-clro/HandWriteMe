import os
from pathlib import Path
from fastapi import HTTPException, status
from app.core.config import settings

class StorageService:
    @staticmethod
    def save_file(contents: bytes, subfolder: str, filename: str) -> tuple[str, str | None]:
        storage_method = (getattr(settings, "STORAGE_METHOD", "file") or "file").lower()
        
        if storage_method == "file":
            base_storage = Path(settings.STORAGE_PATH or "./uploads")
            target_dir = base_storage / subfolder
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / filename
            
            try:
                with open(target_path, "wb") as f:
                    f.write(contents)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not save file to local disk",
                ) from e
                
            file_path_str = str(target_path)
            base_url = (getattr(settings, "STORAGE_BASE_URL", "/uploads") or "/uploads").rstrip("/")
            public_url = f"{base_url}/{subfolder}/{filename}"
            return file_path_str, public_url
            
        elif storage_method == "s3":
            bucket = getattr(settings, "AWS_S3_BUCKET", None) or os.getenv("AWS_S3_BUCKET")
            access_key = getattr(settings, "AWS_ACCESS_KEY_ID", None) or os.getenv("AWS_ACCESS_KEY_ID")
            secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", None) or os.getenv("AWS_SECRET_ACCESS_KEY")
            region = getattr(settings, "AWS_S3_REGION", None) or os.getenv("AWS_S3_REGION", "us-east-1")
            
            if not bucket or not access_key or not secret_key:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="S3 storage is selected but AWS credentials or bucket name are missing.",
                )
                
            try:
                import boto3
                s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region,
                )
                s3_key = f"{subfolder}/{filename}"
                s3_client.put_object(Bucket=bucket, Key=s3_key, Body=contents)
                public_url = f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"
                return f"s3://{bucket}/{s3_key}", public_url
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload file to S3: {str(e)}",
                ) from e

        elif storage_method == "cloudinary":
            cloud_name = getattr(settings, "CLOUDINARY_CLOUD_NAME", None) or os.getenv("CLOUDINARY_CLOUD_NAME")
            api_key = getattr(settings, "CLOUDINARY_API_KEY", None) or os.getenv("CLOUDINARY_API_KEY")
            api_secret = getattr(settings, "CLOUDINARY_API_SECRET", None) or os.getenv("CLOUDINARY_API_SECRET")
            
            if not cloud_name or not api_key or not api_secret:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Cloudinary storage is selected but Cloudinary credentials are missing.",
                )
                
            try:
                import cloudinary
                import cloudinary.uploader
                cloudinary.config(
                    cloud_name=cloud_name,
                    api_key=api_key,
                    api_secret=api_secret,
                )
                res = cloudinary.uploader.upload(contents, folder=subfolder, public_id=filename)
                url = res.get("secure_url") or res.get("url")
                return url, url
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload file to Cloudinary: {str(e)}",
                ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported storage method: {storage_method}",
            )

    @staticmethod
    def delete_file(file_path_str: str | None) -> bool:
        if not file_path_str:
            return False
            
        if file_path_str.startswith("s3://"):
            bucket = getattr(settings, "AWS_S3_BUCKET", None) or os.getenv("AWS_S3_BUCKET")
            access_key = getattr(settings, "AWS_ACCESS_KEY_ID", None) or os.getenv("AWS_ACCESS_KEY_ID")
            secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", None) or os.getenv("AWS_SECRET_ACCESS_KEY")
            region = getattr(settings, "AWS_S3_REGION", None) or os.getenv("AWS_S3_REGION", "us-east-1")
            
            if bucket and access_key and secret_key:
                try:
                    import boto3
                    s3_client = boto3.client(
                        "s3",
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key,
                        region_name=region,
                    )
                    s3_key = file_path_str.replace(f"s3://{bucket}/", "")
                    s3_client.delete_object(Bucket=bucket, Key=s3_key)
                    return True
                except Exception:
                    return False
            return False
            
        # Local file deletion fallback
        if os.path.exists(file_path_str):
            try:
                os.remove(file_path_str)
                return True
            except OSError:
                return False
        return False
