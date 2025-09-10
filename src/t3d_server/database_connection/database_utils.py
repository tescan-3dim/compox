"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from concurrent.futures import ThreadPoolExecutor
import hashlib


class S3FileUploader:
    def __init__(self, s3_client, chunk_size=8 * 1024 * 1024, num_threads=8):
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
        self.s3_client = s3_client
        self.chunk_size = chunk_size
        self.num_threads = num_threads

    def upload_file_multipart(
        self,
        bytes,
        key,
        bucket,
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

        # Create a multipart upload

        response = self.s3_client.create_multipart_upload(Bucket=bucket, Key=key)
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

            # Wait for all parts to be uploaded
            for future in futures:
                future.result()

        # Complete the multipart upload
        parts = [
            {"PartNumber": i + 1, "ETag": part.result()["ETag"]}
            for i, part in enumerate(futures)
        ]
        self.s3_client.complete_multipart_upload(
            Bucket=bucket,
            Key=key,
            MultipartUpload={"Parts": parts},
            UploadId=upload_id,
        )

    def upload_part(self, part, key, bucket, part_number, upload_id):
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
        """
        response = self.s3_client.upload_part(
            Body=part,
            Bucket=bucket,
            Key=key,
            PartNumber=part_number,
            UploadId=upload_id,
        )
        return response


def calculate_etag(bytes_obj):
    """
    Calculate the etag hash of a file, the etag should be the same as the etag
    calculate internally by the boto3/minio client

    Parameters
    ----------
    bytes_obj : str
        The file bytes to calculate the etag hash of.

    Returns
    -------
    str
        The etag hash.

    """
    md5s = hashlib.md5(bytes_obj)
    return '"{}"'.format(md5s.hexdigest())


def calculate_etag_multipart(bytes_obj, chunk_size):
    """
    Calculate the etag hash of a file uploaded using multipart upload. The etag
    should be the same as the etag calculate internally by the boto3/minio client.

    Parameters
    ----------
    bytes_obj : str
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
