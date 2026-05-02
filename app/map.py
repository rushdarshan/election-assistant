from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
import os
from app.stats import record_topic

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/map", response_class=HTMLResponse)
async def map_page(request: Request):
    return templates.TemplateResponse(request=request, name="map.html", context= {
        "request": request,
        "active_nav": "map"
    })

@router.post("/map", response_class=HTMLResponse)
async def fetch_map(request: Request, address: str = Form(...)):
    record_topic("Polling Location")
    api_key = os.getenv("GOOGLE_CIVIC_API_KEY", "")
    
    if not api_key:
        return templates.TemplateResponse(request=request, name="map_result.html", context= {
            "request": request,
            "error": "API Key not configured. Please visit your state's official election website."
        })
        
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://civicinfo.googleapis.com/civicinfo/v2/voterinfo",
                params={"address": address, "key": api_key, "electionId": 2000} # 2000 is usually the standard general election or a test
            )
            # if 2000 fails, we just omit electionId and it defaults to next upcoming
            if resp.status_code != 200:
                resp = await client.get(
                    "https://civicinfo.googleapis.com/civicinfo/v2/voterinfo",
                    params={"address": address, "key": api_key}
                )

            if resp.status_code == 200:
                data = resp.json()
                polling_locations = data.get("pollingLocations", [])
                early_voting = data.get("earlyVoteSites", [])
                state_info = data.get("state", [])
                
                return templates.TemplateResponse(request=request, name="map_result.html", context= {
                    "request": request,
                    "polling_locations": polling_locations,
                    "early_voting": early_voting,
                    "state_info": state_info,
                    "address": address
                })
            else:
                return templates.TemplateResponse(request=request, name="map_result.html", context= {
                    "request": request,
                    "error": "Unable to find polling location for this address. Please visit your state's official election website."
                })
        except Exception as e:
            return templates.TemplateResponse(request=request, name="map_result.html", context= {
                "request": request,
                "error": f"Error looking up address: {str(e)}"
            })
