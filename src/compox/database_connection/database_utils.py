"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import hashlib
import boto3
import time
import random
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
from botocore.exceptions import ClientError


class S3FileUploader:
    """
    File uploader to S3.

    Parameters
    ----------
    s3_client : boto3.client
        The s3 client.
    chunk_size : int
        The size of the chunks to upload. The default is 8 * 1024 * 1024.
    num_threads : int
        The number of threads to use. The default is 8.

    """

    def __init__(
        self,
        s3_client: boto3.client,
        chunk_size: int = 8 * 1024 * 1024,
        num_threads: int = 8,
    ):
        self.s3_client = s3_client
        self.chunk_size = chunk_size
        self.num_threads = num_threads

    def upload_file_multipart(
        self, bytes: bytes, key: str, bucket: str, retries: int = 8
    ) -> None:
        """
        Upload a file to S3 using multipart upload. This is useful for large files.
        We use a thread pool to upload the file in parallel.

        Parameters
        ----------
        bytes : bytes
            The file bytes.
        key : str
            The key of the file in the bucket.
        bucket : str
            The bucket name.
        retries : int
            The number of retries.
        """

        last_err: Exception | None = None

        for attempt in range(retries):
            try:
                return self._upload_file_multipart_step(bytes, key, bucket)
            except ClientError as e:
                last_err = e
                code = e.response.get("Error", {}).get("Code", "")

                # Retry only errors that are plausible transient issues in your Windows+MinIO setup
                transient = code in {
                    "AccessDenied",  # MinIO surfaces some FS errors as AccessDenied
                    "InvalidPart",  # parts temporarily not visible / FS contention
                    "InternalError",
                    "ServiceUnavailable",
                    "SlowDown",
                }

                if (not transient) or (attempt == retries - 1):
                    raise

                sleep_s = min(2.0, 0.1 * (2**attempt)) + random.uniform(0, 0.2)
                logger.warning(
                    f"Multipart upload failed with {code}; retrying "
                    f"(attempt {attempt+1}/{retries}) in {sleep_s:.2f}s: {e}"
                )
                time.sleep(sleep_s)

        raise Exception(
            f"Multipart upload failed after multiple retries: {last_err}"
        )

    def _upload_file_multipart_step(
        self,
        bytes: bytes,
        key: str,
        bucket: str,
    ) -> None:
        """
        Upload a file to S3 using multipart upload. This is useful for large files.
        We use a thread pool to upload the file in parallel.

        Parameters
        ----------
        bytes : bytes
            The file bytes.
        key : str
            The key of the file in the bucket.
        bucket : str
            The bucket name.
        """

        upload_id: str | None = None

        try:
            # Create a multipart upload
            response = self.s3_client.create_multipart_upload(
                Bucket=bucket, Key=key
            )
            upload_id = response["UploadId"]

            # Calculate the number of parts
            num_parts = len(bytes) // self.chunk_size
            if len(bytes) % self.chunk_size != 0 or num_parts == 0:
                num_parts += 1

            # Create a thread pool
            with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
                futures = []
                for i in range(num_parts):
                    start = i * self.chunk_size
                    end = start + self.chunk_size
                    part = bytes[start:end]
                    futures.append(
                        executor.submit(
                            self.upload_part,
                            part,
                            key,
                            bucket,
                            i + 1,
                            upload_id,
                        )
                    )

                # Collect results once (also raises if any part upload failed)
                parts = [f.result() for f in futures]

            # Complete the multipart upload (parts must be sorted by PartNumber)
            parts = sorted(parts, key=lambda p: p["PartNumber"])
            self.s3_client.complete_multipart_upload(
                Bucket=bucket,
                Key=key,
                MultipartUpload={"Parts": parts},
                UploadId=upload_id,
            )

        except Exception:
            # Best-effort cleanup to avoid accumulating unfinished MPUs (critical on Windows)
            if upload_id is not None:
                try:
                    self.s3_client.abort_multipart_upload(
                        Bucket=bucket, Key=key, UploadId=upload_id
                    )
                except Exception as abort_err:
                    logger.warning(
                        f"AbortMultipartUpload failed (ignored): {abort_err}"
                    )
            raise

    def upload_part(
        self,
        part: bytes,
        key: str,
        bucket: str,
        part_number: int,
        upload_id: str,
    ) -> dict:
        """
        Upload a part of a file to S3.

        Parameters
        ----------
        part : bytes
            The part of the file.
        key : str
            The key of the file in the bucket.
        bucket : str
            The bucket name.
        part_number : int
            The part number.
        upload_id : str
            The upload id.

        Returns
        -------
        dict
        """
        response = self.s3_client.upload_part(
            Body=part,
            Bucket=bucket,
            Key=key,
            PartNumber=part_number,
            UploadId=upload_id,
        )
        return {"PartNumber": part_number, "ETag": response["ETag"]}


def calculate_etag(bytes_obj: bytes) -> str:
    """
    Calculate the etag hash of a file, the etag should be the same as the etag
    calculate internally by the boto3/minio client

    Parameters
    ----------
    bytes_obj : bytes
        The file bytes to calculate the etag hash of.

    Returns
    -------
    str
        The etag hash.

    """
    md5s = hashlib.md5(bytes_obj)
    return '"{}"'.format(md5s.hexdigest())


def calculate_etag_multipart(bytes_obj: bytes, chunk_size: int) -> str:
    """
    Calculate the etag hash of a file uploaded using multipart upload. The etag
    should be the same as the etag calculate internally by the boto3/minio client.

    Parameters
    ----------
    bytes_obj : bytes
        The file bytes to calculate the etag hash of.
    chunk_size : int

    Returns
    -------
    str
        The etag hash.
    """

    # Calculate the number of parts
    num_parts = len(bytes_obj) // chunk_size
    if len(bytes_obj) % chunk_size != 0 or num_parts == 0:
        num_parts += 1

    # Calculate the etag of each part
    md5s = []
    for i in range(num_parts):
        start = i * chunk_size
        end = start + chunk_size
        part = bytes_obj[start:end]
        md5s.append(hashlib.md5(part))

    # Calculate the etag of the whole file
    md5 = hashlib.md5()
    for md5_part in md5s:
        md5.update(md5_part.digest())
    return '"{}-{}"'.format(md5.hexdigest(), num_parts)
