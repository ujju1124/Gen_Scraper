"""
Image Proxy Router
Proxies external images to bypass CORS restrictions
"""
import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
import structlog

router = APIRouter()
logger = structlog.get_logger()


@router.get("/proxy")
async def proxy_image(url: str = Query(..., description="Image URL to proxy")):
    """
    Proxy an external image URL to bypass CORS restrictions.
    
    - Fetches the image from the external URL
    - Returns it with appropriate headers
    - Caches the response for performance
    """
    try:
        # Validate URL starts with https
        if not url.startswith("https://"):
            raise HTTPException(status_code=400, detail="Only HTTPS URLs are allowed")
        
        # Fetch the image
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.google.com/"
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to fetch image: {response.status_code}"
                )
            
            # Get content type from response
            content_type = response.headers.get("content-type", "image/jpeg")
            
            # Return the image with appropriate headers
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                    "Access-Control-Allow-Origin": "*",
                }
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Image fetch timeout")
    except httpx.RequestError as e:
        logger.error("image_proxy.request_error", url=url, error=str(e))
        raise HTTPException(status_code=502, detail="Failed to fetch image")
    except Exception as e:
        logger.error("image_proxy.error", url=url, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
