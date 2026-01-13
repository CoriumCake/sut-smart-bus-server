"""
Air Quality Analytics Module
Provides endpoints for air quality data analysis and visualization.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from . import crud
from .database import db

# Get hardware locations collection
hardware_location_collection = db.get_collection("hardware_locations")


async def get_zone_heatmap_data(hours: int = 24, grid_size: float = 0.001, bus_mac: Optional[str] = None):
    """
    Get air quality data grouped by geographic zones for heatmap visualization.
    
    Args:
        hours: Number of hours of historical data to include
        grid_size: Size of grid cells in degrees (0.001 ≈ 111 meters)
    
    Returns:
        List of zone objects with lat, lon, avg_pm25, avg_pm10, count
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    match_stage = {
        "timestamp": {"$gte": cutoff_time},
        "lat": {"$ne": None},
        "lon": {"$ne": None},
        "pm2_5": {"$gt": 0}  # Filter out 0 values (artifacts/missing data)
    }

    if bus_mac:
        match_stage["bus_mac"] = bus_mac

    # Aggregation pipeline to group by grid cells
    pipeline = [
        {
            "$match": match_stage
        },
        {
            "$project": {
                "grid_lat": {
                    "$multiply": [
                        {"$floor": {"$divide": ["$lat", grid_size]}},
                        grid_size
                    ]
                },
                "grid_lon": {
                    "$multiply": [
                        {"$floor": {"$divide": ["$lon", grid_size]}},
                        grid_size
                    ]
                },
                "pm2_5": 1,
                "pm10": 1,
                "timestamp": 1
            }
        },
        {
            "$group": {
                "_id": {
                    "lat": "$grid_lat",
                    "lon": "$grid_lon"
                },
                "avg_pm25": {"$avg": "$pm2_5"},
                "avg_pm10": {"$avg": "$pm10"},
                "max_pm25": {"$max": "$pm2_5"},
                "min_pm25": {"$min": "$pm2_5"},
                "count": {"$sum": 1},
                "last_updated": {"$max": "$timestamp"}
            }
        },
        {
            "$project": {
                "_id": 0,
                "lat": {"$add": ["$_id.lat", grid_size / 2]},  # Center of grid cell
                "lon": {"$add": ["$_id.lon", grid_size / 2]},
                "avg_pm25": {"$round": ["$avg_pm25", 1]},
                "avg_pm10": {"$round": ["$avg_pm10", 1]},
                "max_pm25": {"$round": ["$max_pm25", 1]},
                "min_pm25": {"$round": ["$min_pm25", 1]},
                "count": 1,
                "last_updated": 1
            }
        },
        {"$sort": {"avg_pm25": 1}}  # Sort by air quality (best first)
    ]
    
    try:
        zones = await hardware_location_collection.aggregate(pipeline).to_list(length=500)
        return zones
    except Exception as e:
        print(f"Error in get_zone_heatmap_data: {e}")
        return []


async def get_time_series_data(hours: int = 24, interval_minutes: int = 60, bus_mac: Optional[str] = None):
    """
    Get air quality time series data for trend visualization.
    
    Args:
        hours: Number of hours of data to include
        hours: Number of hours of data to include
        interval_minutes: Aggregation interval in minutes
        bus_mac: Optional MAC address to filter by specific bus
    
    Returns:
        List of time-bucketed averages with timestamp, avg_pm25, avg_pm10
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    match_stage = {
        "timestamp": {"$gte": cutoff_time},
        "pm2_5": {"$gt": 0}  # Filter out 0 values
    }
    
    if bus_mac:
        match_stage["bus_mac"] = bus_mac

    pipeline = [
        {
            "$match": match_stage
        },
        {
            "$group": {
                "_id": {
                    "$dateTrunc": {
                        "date": "$timestamp",
                        "unit": "minute",
                        "binSize": interval_minutes
                    }
                },
                "avg_pm25": {"$avg": "$pm2_5"},
                "avg_pm10": {"$avg": "$pm10"},
                "avg_temp": {"$avg": "$temp"},
                "avg_hum": {"$avg": "$hum"},
                "count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "timestamp": "$_id",
                "avg_pm25": {"$round": ["$avg_pm25", 1]},
                "avg_pm10": {"$round": ["$avg_pm10", 1]},
                "avg_temp": {"$round": ["$avg_temp", 1]},
                "avg_hum": {"$round": ["$avg_hum", 0]},
                "count": 1
            }
        },
        {"$sort": {"timestamp": 1}}
    ]
    
    try:
        series = await hardware_location_collection.aggregate(pipeline).to_list(length=500)
        return series
    except Exception as e:
        print(f"Error in get_time_series_data: {e}")
        return []


async def get_overall_stats(hours: int = 24, bus_mac: Optional[str] = None):
    """
    Get overall air quality statistics for the dashboard summary.
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    match_stage = {
        "timestamp": {"$gte": cutoff_time},
        "pm2_5": {"$gt": 0}  # Filter out 0 values
    }

    if bus_mac:
        match_stage["bus_mac"] = bus_mac

    pipeline = [
        {
            "$match": match_stage
        },
        {
            "$group": {
                "_id": None,
                "avg_pm25": {"$avg": "$pm2_5"},
                "avg_pm10": {"$avg": "$pm10"},
                "max_pm25": {"$max": "$pm2_5"},
                "min_pm25": {"$min": "$pm2_5"},
                "avg_temp": {"$avg": "$temp"},
                "avg_hum": {"$avg": "$hum"},
                "total_readings": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "avg_pm25": {"$round": ["$avg_pm25", 1]},
                "avg_pm10": {"$round": ["$avg_pm10", 1]},
                "max_pm25": {"$round": ["$max_pm25", 1]},
                "min_pm25": {"$round": ["$min_pm25", 1]},
                "avg_temp": {"$round": ["$avg_temp", 1]},
                "avg_hum": {"$round": ["$avg_hum", 0]},
                "total_readings": 1
            }
        }
    ]
    
    try:
        result = await hardware_location_collection.aggregate(pipeline).to_list(length=1)
        if result:
            return result[0]
        return {
            "avg_pm25": 0,
            "avg_pm10": 0,
            "max_pm25": 0,
            "min_pm25": 0,
            "avg_temp": 0,
            "avg_hum": 0,
            "total_readings": 0
        }
    except Exception as e:
        print(f"Error in get_overall_stats: {e}")
        return {"error": str(e)}
