"""
Copyright 2026 Tescan group, a.s.
All rights reserved
"""

from starlette.responses import StreamingResponse


class OctetStreamResponse(StreamingResponse):
    media_type = "application/octet-stream"
