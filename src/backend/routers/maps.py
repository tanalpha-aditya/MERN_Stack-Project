from fastapi import APIRouter, HTTPException, Depends, status, Cookie, Request
from pydantic import BaseModel
from typing import Optional
# from enum import Enum
# from os import getenv
from typing import Optional, List
from db import db
from routers.admin import check_current_admin
# from routers.users import check_current_user, get_current_user

router = APIRouter()

#Define the model for the parking location
class Location(BaseModel):
    locid: int
    name: str
    city: str
    state: str
    country: str
    landmark: Optional[str] = None
    pin_code: int

# Define the model for the parking map
class Map(BaseModel):
    mapid: int
    locid: int
    floor: str
    parking_slots: list
    robot_ids: list = []
    operations: list = []
    map_url: str

class ManyLocationsResponse(BaseModel):
    locations: List[Location] | None

class ManyMapsResponse(BaseModel):
    maps: List[Map] | None

def get_parking_location_by_id(id: int):
    try:
        pl = db.locations.find_one({"locid": id}, {"_id": 0})
        if pl:
            return Location(**pl)
        return None
    except Exception:
        return None
    


def get_parking_location_by_pin(pin: int):
    try:
        pl = db.locations.find_one({"pin": pin}, {"_id": 0})
        if pl:
            return Location(**pl)
        return None
    except Exception:
        return None

def get_parking_location_id():
    pl = list(db.locations.find({}, {"locid":1, "_id": 0}))
    l=list()
    for i in pl:
        l.append(i["locid"])
    l.sort(reverse=True)
    if len(l) == 0:
        return 0
    return 1 + l[0]

def get_parking_map_id():
    maps = list(db.maps.find({}, {"mapid": 1, "_id": 0}))
    map_ids = [m["mapid"] for m in maps]
    map_ids.sort(reverse=True)
    if len(map_ids) == 0:
        return 0
    return 1 + map_ids[0]
    
# Endpoint to get all parking locations
@router.get("/locations")
def get_locations(request: Request):
    locations = list(db.locations.find({}, {"_id": 0}))
    if len(locations):
        return ManyLocationsResponse(locations = locations)
    return None

# Endpoint to get all parking maps (irrespective of location)
@router.get("/maps")
def get_maps(request: Request, is_admin: bool = Depends(check_current_admin)):
    if not is_admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unauthorized")
    maps = list(db.maps.find({}, {"_id": 0}))
    if len(maps):
        return ManyMapsResponse(maps = maps)
    return None

# Endpoint to get all parking locations for a particular location
@router.get("/maps/{locid}")
def get_map_locid(request: Request, locid: int):
    maps = list(db.maps.find({"locid":locid}, {"_id": 0}))
    if len(maps):
        return ManyMapsResponse(maps=maps)
    return None

#Endpoint to add a new parking location
@router.post("/new-location")
def add_parking_location(location: Location, is_admin: bool = Depends(check_current_admin)):
    if not is_admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unauthorized")
    location.locid = get_parking_location_id()

    if get_parking_location_by_pin(location.pin_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Parking location already registered")
    
    existing_location = db.locations.find_one({"name": location.name,
                                               "city": location.city,
                                               "state": location.state,
                                               "country": location.country},
                                              {"_id": 0})
    if existing_location:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Exact location details already exist")
    
    if(len(str(location.pin_code)) != 6):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid Pin Code!")
    db.locations.insert_one(location.dict())
    return {"locid": location.locid}

#Endpoint to add a new parking map
@router.post("/new-map")
def add_parking_map(map: Map, is_admin: bool = Depends(check_current_admin)):
    if not is_admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unauthorized")
    # Check if the map URL already exists
    existing_map = db.maps.find_one({"map_url": map.map_url}, {"_id": 0})
    if existing_map:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Map URL already exists")

    existing_map = db.maps.find_one({"location": map.locid, 
                                      "floor": map.floor, 
                                      "parking_slots": map.parking_slots},
                                     {"_id": 0})
    if existing_map:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Exact map details already exist")
    
    map.mapid = get_parking_map_id()
    
    db.maps.insert_one(map.dict())
    return {"mapid": map.mapid}

# Endpoint to remove a parking location by id
@router.delete("/parking-locations/{locid}")
def remove_parking_location(locid: int, is_admin: bool = Depends(check_current_admin)):
    if not is_admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unauthorized")
    pl = get_parking_location_by_id(locid)
    if pl:
        maps = db.maps.find({"locid": locid})
        if maps:
            db.maps.delete_many({"locid": locid})
        
        db.locations.delete_one({"locid": locid})
        return {"message": "Parking Location deleted successfully!"}
    raise HTTPException(status_code=404, detail="Parking Location not Found!")

#Endpoint to get a single parking location by id
@router.get("/parking-locations/{locid}")
def get_parking_location(locid: int):
    pl = get_parking_location_by_id(locid)
    if pl:
        return pl
    raise HTTPException(status_code=404, detail="Parking Location not Found!")
