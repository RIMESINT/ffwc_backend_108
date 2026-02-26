SESAME_USERS = {
    "status": {
        "APPROVED": 1,
        "PENDING":  2,
        "REJECTED": 3
    },
    "roles": {
        1: "SUPER ADMIN",
        2: "COUNTRY ADMIN",
        3: "USER"
    }
}


PAGINATION_CONSTANT = {
    "page_size":10,
    "max_page_size": 100,
    "page_size_query_param": 'page_size'
}


GEO_DATA = {
    "Bangladesh": {
        "Country": {
            "field_type_id": 0,
            "parent_id": None
        },
        "Div": {
            "field_type_id": 1 
        },
        "Dis": {
            "field_type_id": 2 
        },
        "Upz": {
            "field_type_id": 3 
        },
        "Union": {
            "field_type_id": 4 
        },
        "Ward": {
            "field_type_id": 5 
        }
    },
    "BHUTAN": {
        "country_id": 24
    },
    "TL": {
        "country_id": 19
    }
}


GEO_LEVELS = { 
    "BD": {
        "Country": {
            "id": 0,
            "ordering": 0,
            "parent_id": None,
            "parent_is_null": True
        },
        "Division": {
            "id": 1,
            "ordering": 1 
        },
        "District": {
            "id": 2,
            "ordering": 2 
        },
        "Upazilla": {
            "id": 3,
            "ordering": 3 
        },
        "Union": {
            "ordering": 4 
        },
        "Ward": {
            "ordering": 5 
        }   
    },
    "BHUTAN": {
        "Country": {
            "id": 60,
            "ordering": 0,
            "parent_id": None,
            "parent_is_null": True
        },
        "District": {
            "id": 61,
            "ordering": 1 
        },
        "Subdistrict": {
            "id": 62,
            "ordering": 2 
        },
    } 
}

# GEO_DATA_LEVEL_DETAILS = {

# }


DIRECTORY = {
    "user_authentication":{
        "profile_pic": "crop/profile/" 
    },
    "crop_crop_image":{
        "crop_image": "crops/crops/" 
    },
    "shape_file_upload_by_date":{
        "__comment_1": "...Inside MEDIA Folder...",
        "upload_shape_file": "data/uploaded_shape_file/" 
    },
    "crop_variety":{
        "__comment_2": "...Inside MEDIA Folder...",
        "cv_shape_file_upload": "data/crop_variety_shape_file/" 
    },
    "crop_stage":{
        "__comment_3": "...Inside MEDIA Folder...",
        "cs_img_upload": "data/crop_stage_file/image/" 
    },
    "app_pest": {
        "crop_stage":{
            "__comment_4": "...Inside MEDIA Folder...",
            "pest_img_upload": "pests/pest_image/" 
        },
    },
    "app_disease": {
        "crop_stage":{
            "__comment_5": "...Inside MEDIA Folder...",
            "disease_img_upload": "diseases/disease_image/" 
        },
    },
    "app_generic": {
        "crop_stage":{
            "__comment_4": "...Inside MEDIA Folder...",
            "generic_img_upload": "generics/generic_image/" 
        },
    },
    "app_dissemination": {
        "am_bulletin_pdf": "app_dissemination/am_bulletin/"
    }
}

APP_WEATHER_API = {
    "management_command":{  
        1: "BMDWRF_LOC",
        2: "ECMWF_LOC",
        3: "ECMWF_HRES_VIS",
        4: "NCHM_LOC",
        5: "CST",
        6: "CST_MONTHLY",
        7: "RIMESWRF_DAILY_LOC",
        8: "ECMWF_SEAS_MONTHLY_LOC",
        9: "ECMWF_SEAS_SEASONAL_LOC"
    },
    "source":{
        1: "BMDWRF",
        2: "ECMWF",
        3: "RIMESWRF",
        4: "ECMWF_HRES_VIS"
    },
    "parameter": {
        "rf": 1,
        "temp": 2,
        "rh": 3,
        "tempdew": 4,
        "smois": 5,
        "windspd": 6,
        "winddir": 7,
        "cldcvr": 8,
        "windgust": 9,
        "thi": 10,
        "et0": 11,
        "tmax": 12,
        "tmin": 13
    }
}

APP_WEATHER_ALERT = {
    "alert_type": {
        "Normal": 1,
        "Moderate": 2,
        "Heavy": 3,
        "Extreme": 4,
        "rain_alert": {
            "Normal": 1,
            "Moderate": 2,
            "Heavy": 3,
            "Extreme": 4,
        },
        "heat_wave": {
            "Normal": 5,
            "Moderate Heat": 6,
            "Hot": 7,
            "Very Hot": 8,
        },
        "cold_wave": {
            "Normal": 9,
            "Moderate Cold": 10,
            "Cold": 11,
            "Very Cold": 12,
        },
        "wind_alert": {
            "Normal": 13,
            "Moderate": 14,
            "Heavy": 15,
            "Extreme": 16,
        },
        "thi_alert": {
            "Normal": 1,
            "Moderate": 2,
            "Heavy": 3,
            "Extreme": 4,
        },

    },
    "alert_category": {
        "heat_wave": 1,
        "cold_wave": 2,
        "rain_alert": 3,
        "wind_alert": 4,
        "thi_alert": 5,
    }
}
    
APP_GENERIC_ADVISORY = { 
    "gen_alert_type":{
        "Above": 1,
        "Within": 2,
        "Below": 3
    }
}

APP_DISEASE = {
    "fav_con_conf_group" : {
        1: "AND",
        2: "OR",
    },
    "advisory_type" : {
        "Daily": 1,
        "Weekly": 2,
        "Monthly": 3,
    }
}

APP_DISSEMINATION = {
    "dissemination_status" : {
        "Failed": 0,
        "Sent": 1,
        "Pending": 2,
    }
}

APP_DYNAMIC_MENU = {
    "menu_type": {
        "Dashboard": 1
    }
}

GLOBAL_VARIABLES = {
    
}


app_visualization = {
    "bd_details_OLD": {
        "SHORT_NAME": "bd",
        "BD_LAT_MIN": 22.0,
        "BD_LAT_MAX": 28.0,
        "BD_LON_MIN": 86.0,
        "BD_LON_MAX": 97.0,

    },
    "bd_details": {
        "SHORT_NAME": "bd",
        "BD_LAT_MIN": 20.0,
        "BD_LAT_MAX": 32.0,
        "BD_LON_MIN": 72.0,
        "BD_LON_MAX": 98.0,

    },
    "system_state_name": {
        1: "ECMWF_HRES_VIS_DAILY", 
        2: "BMDWRF_HRES_VIS_DAILY", 
        6: "IMD_GFS_VIS_DAILY", 
        8: "IMD_WRF_VIS_DAILY", 
        3: "BMDWRF_LOC_DAILY",
        4: "ECMWFF_HRES_LOC_DAILY",
        5: "IMD_GFS_LOC_DAILY",
        7: "IMD_WRF_LOC_DAILY",
        12: "UKMET_DETERMINISTIC_VIS_DAILY",
        13: "UKMET_DETERMINISTIC_LOC_DAILY",

        9: "IMD_STATION_OBS_DAILY",
        10: "FFWC_STATION_OBS_DAILY",
        11: "BMD_STATION_OBS_DAILY",
        12: "MSWEP_OBS_DAILY",

        20: "FFWC_STREAM_FLOW_FORECAST_DAILY",
    },
    "source": {
        "ECMWF_HRES_VIS": 1, 
        "BMDWRF_HRES_VIS": 2,  
    },
    "bmdwrf": {
        "JSON_OUT_LOC": "/uploads/assets/bmd_wrf/forecast_map/", 
        "WRF_NC_LOC": "/forecast/bmd_wrf/", 
    },
    "ecmwf_hres": {
        "JSON_OUT_LOC_ECMWF_HRES": "/uploads/assets/ecmwrf_hres/forecast_map/", 
        "WRF_NC_LOC_ECMWF_HRES": "/forecast/ecmwrf_hres/",
    }
}