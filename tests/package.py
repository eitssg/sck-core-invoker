import os
import tempfile

import core_logging as log

from core_framework.models import PackageDetails
from core_helper.magic import MagicS3Client, MagicBucket

import zipfile


def upload_package(package: PackageDetails):
    """
    Upload a deployment package to S3 by creating a zip file containing the platform structure.

    Creates a temporary zip file containing:
    - deployspec.yaml (at root level)
    - platform/components/ directory structure
    - platform/vars/ directory structure

    The zip file is uploaded to S3 using the bucket and key specified in the PackageDetails.

    :param package: Package details containing S3 destination information
    :type package: PackageDetails
    :raises Exception: If package upload fails for any reason

    Example:
        >>> package = PackageDetails(
        ...     bucket_name="my-bucket",
        ...     bucket_region="us-east-1",
        ...     key="packages/my-app/1.0.0/package.zip"
        ... )
        >>> upload_package(package)
    """
    # UPLOAD action to upload our package to the system
    # PackageDetails is Pydantic: snake_case attributes
    dirname = os.path.join(os.path.dirname(os.path.realpath(__file__)), "platform")

    # Create temporary file but don't use context manager that keeps it open
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    temp_file_path = temp_file.name
    temp_file.close()  # ✅ Close the file so Windows allows other processes to access it

    try:
        log.info(f"Creating deployment package from {dirname}")

        # Create a zip file with the package contents
        with zipfile.ZipFile(temp_file_path, "w", zipfile.ZIP_DEFLATED) as zip_file:

            # Add deployspec.yaml to root of zip
            deployspec_path = os.path.join(dirname, "deployspec.yaml")
            if os.path.exists(deployspec_path):
                zip_file.write(deployspec_path, arcname="deployspec.yaml")
                log.debug("Added deployspec.yaml to package")

            # Add all components directories with platform/ prefix
            components_dir = os.path.join(dirname, "components")
            if os.path.exists(components_dir):
                for root, dirs, files in os.walk(components_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, dirname)
                        zip_file.write(file_path, arcname=arcname)
                        log.debug(f"Added {arcname} to package")

            # Add all vars directories with platform/ prefix
            vars_dir = os.path.join(dirname, "vars")
            if os.path.exists(vars_dir):
                for root, dirs, files in os.walk(vars_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, dirname)
                        zip_file.write(file_path, arcname=arcname)
                        log.debug(f"Added {arcname} to package")

        # Upload to S3
        log.info(
            f"Uploading package to s3://{package.bucket_name}/{package.key}",
            details=package.model_dump(),
        )
        bucket: MagicBucket = MagicS3Client.get_bucket(Region=package.bucket_region, BucketName=package.bucket_name)

        bucket.put_object(
            Body=open(temp_file_path, "rb"),
            Key=package.key,
            ExtraArgs={"ContentType": "application/zip", "ACL": "private"},
        )

        log.info("Package uploaded successfully")

    except Exception as e:
        log.error(f"Failed to upload package: {e}")
        raise
    finally:
        # ✅ Clean up the temporary file
        try:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                log.debug(f"Cleaned up temporary file: {temp_file_path}")
        except Exception as cleanup_error:
            log.warning(f"Failed to clean up temporary file: {cleanup_error}")
