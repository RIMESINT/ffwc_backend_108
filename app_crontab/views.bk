# app_crontab/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from celery.result import AsyncResult
from celery import states

from .tasks import run_crontab_script_async

# Dictionary registry containing only the active blocks defined in cronjob.txt
PRODUCTION_PIPELINE_REGISTRY = {
    "section_1_housekeeping": {
        "title": "1. Core Observations & Housekeeping",
        "description": "Primary telemetry ingestion scripts and automated filesystem cleaning routines.",
        "tasks": {
            "indian_water": {
                "name": "Generate Indian Station Water",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/shell-scripts/shellScripts/generate_indian_station_water.sh"]
            },
            "mswep_download": {
                "name": "Download MSWEP Precipitation Stream",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/shell-scripts/download_MSWEP.sh"]
            },
            "imd_station_process": {
                "name": "Observation IMD Stations Wise Process",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/observation_imd_stations_wise_process.sh"]
            },
            "delete_old_files": {
                "name": "Delete Old Files and Data Records",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/delete_old_files_and_data.sh"]
            }
        }
    },
    "section_2_summaries": {
        "title": "2. Rainfall & Flood Summaries",
        "description": "Visual report compilers and spatial mapping distribution canvas construction routines.",
        "tasks": {
            "rainfall_map_v1": {
                "name": "Generate Rainfall Distribution Map (V1)",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/shell-scripts/generate_rainfall_distribution_map.sh"]
            },
            "rainfall_map_v2": {
                "name": "Generate Rainfall Distribution Map (V2)",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/shell-scripts/generate_rainfall_distribution_map_v2.sh"]
            },
            "flood_summary": {
                "name": "Generate Flood Summary Report",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/shell-scripts/generate_flood_summary.sh"]
            }
        }
    },
    "section_3_bmd": {
        "title": "3. BMD Source Block & Anomalies",
        "description": "Bangladesh Meteorological Department high-resolution pipelines and spatial anomalies grids.",
        "tasks": {
            "bmd_download_sh": {
                "name": "Download & Crop BMDWRF HRES Data (Shell Script)",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/download_crop_bmdwrf_hres_data.sh"]
            },
            "bmd_download_py": {
                "name": "Download & Crop BMDWRF HRES Data (Django Python Task)",
                "args": ["bash", "-lc", "/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3 /home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py download_crop_bmdwrf_hres_data"]
            },
            "bmd_monsoon_flash": {
                "name": "Generate BMDWRF Monsoon Basin Wise Flash Flood",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_bmdwrf_monsoon_basin_wise_flash_flood"]
            },
            "bmd_pre_monsoon_flash": {
                "name": "Generate BMDWRF Pre-Monsoon Basin Wise Flash Flood",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_bmdwrf_pre_monsoon_basin_wise_flash_flood"]
            },
            "bmd_basin_forecast_py": {
                "name": "Basin Wise Forecast BMDWRF (Django Command Interface)",
                "args": ["bash", "-lc", "/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3 /home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py basin_wise_forecast_bmdwrf"]
            },
            "bmd_vis_map_py": {
                "name": "Visualize BMD WRF Process Forecast Map (Python Core)",
                "args": ["bash", "-lc", "/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3 /home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py vis_bmd_wrf_process_forecast_map"]
            },
            "bmd_vis_map_sh": {
                "name": "Visualize BMD WRF Process Forecast Map (Shell Component Script)",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/vis_bmd_wrf_process_forecast_map.sh"]
            },
            "bmd_basin_forecast_sh": {
                "name": "Basin Wise Forecast BMDWRF Grid (Shell Executable Terminal)",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/basin_wise_forecast_bmdwrf.sh"]
            },
            "bmd_anomaly_base": {
                "name": "Compute BMD Forecasting Spatial Anomalies Matrix",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "compute_bmd_anomaly"]
            },
            "bmd_anomaly_rasters": {
                "name": "Generate BMD Spatial Anomaly Mapping Rasters",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_bmd_anomaly_rasters"]
            },
            "bmd_weekly_anomaly": {
                "name": "Compute BMD Long-Range Weekly Running Anomalies",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "compute_bmd_weekly_anomaly"]
            },
            "bmd_weekly_rasters": {
                "name": "Generate BMD Weekly Raster Data Format Canvas Maps",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_bmd_weekly_rasters"]
            }
        }
    },
    "section_4_ukmet": {
        "title": "4. UKMET Source Block & Anomalies",
        "description": "United Kingdom Meteorological Office data collection streams and anomaly projection canvas algorithms.",
        "tasks": {
            "ukmet_download_det": {
                "name": "Download UKMET Deterministic Forecast Model Data",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "download_ukmet_det_forecast"]
            },
            "ukmet_download_ens": {
                "name": "Download UKMET Probabilistic Ensemble Datasets",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "download_ukmet_ensemble"]
            },
            "ukmet_monsoon_det": {
                "name": "Generate UKMET Monsoon Deterministic Basin Wise Flash Flood",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_ukmet_monsoon_det_basin_wise_flash_flood"]
            },
            "ukmet_pre_monsoon_det": {
                "name": "Generate UKMET Pre-Monsoon Deterministic Basin Wise Flash Flood",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_ukmet_pre_monsoon_det_basin_wise_flash_flood"]
            },
            "ukmet_monsoon_prob": {
                "name": "Generate UKMET Monsoon Probabilistic Flash Flood Projections",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_ukmet_monsoon_probabilistic_flash_flood"]
            },
            "ukmet_pre_monsoon_prob": {
                "name": "Generate UKMET Pre-Monsoon Probabilistic Flash Flood Projections",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_ukmet_pre_monsoon_probabilistic_flash_flood"]
            },
            "ukmet_vis_map_py": {
                "name": "Visualize UKMET Deterministic Process Forecast Map (Python Module)",
                "args": ["bash", "-lc", "/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3 /home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py vis_ukmet_deterministic_process_forecast_map"]
            },
            "ukmet_basin_forecast_py": {
                "name": "Basin Wise Forecast UKMET Deterministic (Python Context Interface)",
                "args": ["bash", "-lc", "/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3 /home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py basin_wise_forecast_ukmet_deterministic"]
            },
            "ukmet_vis_map_sh": {
                "name": "Visualize UKMET Deterministic Process Forecast Map (Shell Script Launcher)",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/vis_ukmet_deterministic_process_forecast_map.sh"]
            },
            "ukmet_basin_forecast_sh": {
                "name": "Basin Wise Forecast UKMET Deterministic (Shell Script Executable)",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/basin_wise_forecast_ukmet_deterministic.sh"]
            },
            "ukmet_anomaly_base": {
                "name": "Compute UKMET Forecasting Spatial Anomaly Arrays",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "compute_ukmet_anomaly"]
            },
            "ukmet_anomaly_rasters": {
                "name": "Generate UKMET Spatial Anomaly Mapping Rasters",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_ukmet_anomaly_rasters"]
            },
            "ukmet_weekly_anomaly": {
                "name": "Compute UKMET Aggregated Weekly Running Trend Anomalies",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "compute_ukmet_weekly_anomaly"]
            },
            "ukmet_weekly_rasters": {
                "name": "Generate UKMET Weekly Running Trend Raster Data Formats",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_ukmet_weekly_rasters"]
            }
        }
    },
    "section_5_ecmwf": {
        "title": "5. ECMWF Source Block & Anomalies",
        "description": "European Centre for Medium-Range Weather Forecasts high-precision resolution models.",
        "tasks": {
            "ecmwf_download_01": {
                "name": "Download ECMWF 0.1 High Resolution Core Forecast Grid",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "download_ecmwf_0_1_forecast"]
            },
            "ecmwf_download_02": {
                "name": "Download ECMWF 0.2 Standard Resolution Core Forecast Grid",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "download_ecmwf_0_2_forecast"]
            },
            "ecmwf_download_ens": {
                "name": "Download ECMWF Core Probabilistic Ensemble Grids Data",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "download_ecmwf_ens_forecast"]
            },
            "ecmwf_monsoon_basin_flash": {
                "name": "Generate ECMWF 0.2 Monsoon Basin Wise Flash Flood Predictions",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_ecmwf_0_2_monsoon_basin_wise_flash_flood"]
            },
            "ecmwf_pre_monsoon_basin_flash": {
                "name": "Generate ECMWF 0.2 Pre-Monsoon Basin Wise Flash Flood Predictions",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_ecmwf_0_2_pre_monsoon_basin_wise_flash_flood"]
            },
            "ecmwf_monsoon_prob_flash": {
                "name": "Generate ECMWF Monsoon Probabilistic Basin Flash Flood Projections",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_ecmwf_monsoon_probabilistic_flash_flood"]
            },
            "ecmwf_pre_monsoon_prob_flash": {
                "name": "Generate ECMWF Pre-Monsoon Probabilistic Basin Flash Flood Projections",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_ecmwf_pre_monsoon_probabilistic_flash_flood"]
            },
            "ecmwf_crop_hres": {
                "name": "Download & Crop ECMWF HRES Boundary Data (Shell Component Script)",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/download_crop_ecmwf_hres_data.sh"]
            },
            "ecmwf_vis_map": {
                "name": "Visualize ECMWF HRES Dynamic Processing Forecast Maps Grids",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/vis_ecmwf_hres_process_forecast_map.sh"]
            },
            "ecmwf_basin_forecast": {
                "name": "Basin Wise Forecast ECMWF HRES Numerical Calculations Grid",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/basin_wise_forecast_ecmwf_hres.sh"]
            },
            "ecmwf_anomaly_base": {
                "name": "Compute Base ECMWF Matrix Spatial Forecasting Anomalies Trends",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "compute_ecmwf_anomaly"]
            },
            "ecmwf_anomaly_rasters": {
                "name": "Generate ECMWF Matrix Spatial Anomaly Projection Surface Rasters",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_ecmwf_anomaly_rasters"]
            },
            "ecmwf_weekly_anomaly": {
                "name": "Compute ECMWF Long-Range Weekly Running Trend Anomalies Data",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "compute_ecmwf_weekly_anomaly"]
            },
            "ecmwf_weekly_rasters": {
                "name": "Generate ECMWF Weekly Running Trend Spatial Raster Canvas Maps",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_ecmwf_weekly_rasters"]
            }
        }
    },
    "section_6_imd": {
        "title": "6. IMD SOURCE BLOCK & ANOMALIES",
        "description": "India Meteorological Department GFS and WRF boundary tracking model components.",
        "tasks": {
            "imd_gfs_download": {
                "name": "Download, Convert & Crop IMD GFS Resolution Boundary Data",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/download_convert_crop_imd_gfs_data.sh"]
            },
            "imd_wrf_download": {
                "name": "Download, Merge & Crop IMD WRF Mesoscale Regional Boundaries Data",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/download_merge_crop_imd_wrf_data.sh"]
            },
            "imd_gfs_vis": {
                "name": "Visualize IMD GFS Processing Forecast Numerical Matrix Maps",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/vis_imd_gfs_process_forecast_map.sh"]
            },
            "imd_wrf_vis": {
                "name": "Visualize IMD WRF Processing Forecast Numerical Matrix Maps",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/vis_imd_wrf_process_forecast_map.sh"]
            },
            "imd_gfs_basin": {
                "name": "Calculate Basin Wise Forecast via IMD GFS Extrapolations Data",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/basin_wise_forecast_imd_gfs.sh"]
            },
            "imd_wrf_basin": {
                "name": "Calculate Basin Wise Forecast via IMD WRF Extrapolations Data",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/basin_wise_forecast_imd_wrf.sh"]
            },
            "imd_gfs_anomaly_base": {
                "name": "Compute IMD GFS Grid Forecasting Spatial Anomalies Core",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "compute_imd_gfs_anomaly"]
            },
            "imd_gfs_anomaly_rasters": {
                "name": "Generate IMD GFS Matrix Spatial Anomaly Projection Rasters Data",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_imd_gfs_anomaly_rasters"]
            },
            "imd_gfs_weekly_anomaly": {
                "name": "Compute IMD GFS Aggregated Weekly Running Anomalies Metric",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "compute_imd_gfs_weekly_anomaly"]
            },
            "imd_gfs_weekly_rasters": {
                "name": "Generate IMD GFS Weekly Anomaly Mapping Rasters Data Canvas",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_imd_gfs_weekly_rasters"]
            }
        }
    },
    "section_7_station_forecasts": {
        "title": "7. STATION FORECASTS & SHARED SCRIPTS",
        "description": "Localized gauge discharge metrics and shared programmatic flash flood forecast computations.",
        "tasks": {
            "forecast_amalshid": {
                "name": "Generate Forecast: Amalshid Station Gauge",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_forecast_amalshid"]
            },
            "forecast_cumilla": {
                "name": "Generate Forecast: Cumilla Station Gauge",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_forecast_cumilla"]
            },
            "forecast_dalia": {
                "name": "Generate Forecast: Dalia Station Gauge",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_forecast_dalia"]
            },
            "forecast_sunamganj": {
                "name": "Generate Forecast: Sunamganj Station Gauge",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_forecast_sunamganj"]
            },
            
            
            "forecast_brahmaputra": {
                "name": "Generate Forecast: Brahmaputra Station Gauge",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_forecast_brahmaputra"]
            },
            
            "forecast_ganges": {
                "name": "Generate Forecast: Ganges Station Gauge",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_forecast_ganges"]
            },
            
            
            "forecast_sylhet": {
                "name": "Generate Forecast: Sylhet Station Gauge",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_forecast_sylhet"]
            },
            
            
            "forecast_parshuram": {
                "name": "Generate Forecast: Parshuram Station Gauge",
                "args": ["/home/rimes/.pyenv/versions/ffwc_rebase/bin/python3", "/home/rimes/ffwc-rebase/backend/ffwc_django_project/manage.py", "generate_forecast_parshuram"]
            },
            
            
            "streamflow_forecast": {
                "name": "Download Stream Flow Forecast Data (Shell Script)",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/app_crontab/bash_script/ffwc_108_rebase/app_visualization/download_stream_flow_forecast_data.sh"]
            },
            "monsoon_basin_flash_flood": {
                "name": "Generate Monsoon Basin Wise Flash Flood",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/shell-scripts/generate_monsoon_basin_wise_flash_flood.sh"]
            },
            "ukmet_monsoon_basin": {
                "name": "Generate UKMET Monsoon Basin Wise Flash Flood",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/shell-scripts/generate_ukmet_monsoon_basin_wise_flash_flood.sh"]
            },
            "monsoon_probabilistic": {
                "name": "Generate Monsoon Probabilistic Flash Flood",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/shell-scripts/generate_monsoon_probabilistic_flash_flood.sh"]
            },
            "ukmet_monsoon_probabilistic": {
                "name": "Generate UKMET Monsoon Probabilistic Flash Flood",
                "args": ["/home/rimes/ffwc-rebase/backend/ffwc_django_project/shell-scripts/generate_ukmet_monsoon_probabilistic_flash_flood.sh"]
            }
        }
    }
}

@staff_member_required
def crontab_dashboard_view(request):
    """Renders the single-environment crontab core monitoring operations matrix page."""
    from django.contrib import admin
    context = admin.site.each_context(request)
    context.update({
        'title': 'Operational Pipelines Production Controller Workspace',
        'pipeline_registry': PRODUCTION_PIPELINE_REGISTRY,
    })
    return render(request, 'admin/app_crontab/dashboard.html', context)

@staff_member_required
@csrf_protect
@require_POST
def crontab_trigger_json_view(request):
    """Secure endpoint routing action codes dynamically to background task configurations."""
    section_key = request.POST.get('section_key')
    task_key = request.POST.get('task_key')
    
    section_meta = PRODUCTION_PIPELINE_REGISTRY.get(section_key)
    script_meta = section_meta['tasks'].get(task_key) if section_meta else None

    if not script_meta:
        return JsonResponse({'status': 'error', 'message': 'The targeted pipeline parameter array mapping is invalid.'}, status=400)

    try:
        task = run_crontab_script_async.delay(script_meta['name'], script_meta['args'])
        return JsonResponse({
            'status': 'success',
            'message': f"Successfully launched backend process framework for: {script_meta['name']}",
            'task_id': task.id
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f"Failed to access Celery task broker lines: {str(e)}"}, status=500)

@staff_member_required
def crontab_task_status_view(request, task_id):
    """Poll endpoint reading execution diagnostic frames from the active celery metadata tables backend."""
    result = AsyncResult(task_id)
    response_data = {
        'state': result.state,
        'percent': 0,
        'message': 'Allocating tracking metrics from worker thread channels...',
        'stdout': '',
        'stderr': ''
    }

    if isinstance(result.info, dict):
        response_data['percent'] = result.info.get('percent', 0)
        response_data['message'] = result.info.get('description', 'Processing file layout structures...')
        
    if result.state == states.SUCCESS:
        meta_info = result.result
        if isinstance(meta_info, dict):
            raw_stderr = meta_info.get('stderr', '')
            # Filter out deprecation warnings line by line cleanly
            filtered_stderr = "\n".join([line for line in raw_stderr.splitlines() if 'DeprecationWarning' not in line])
            
            response_data.update({
                'percent': 100,
                'message': meta_info.get('message', 'Completed successfully.'),
                'stdout': meta_info.get('stdout', ''),
                'stderr': filtered_stderr
            })
    elif result.state == states.FAILURE:
        raw_stderr = str(result.result)
        filtered_stderr = "\n".join([line for line in raw_stderr.splitlines() if 'DeprecationWarning' not in line])
        
        response_data.update({
            'percent': 100,
            'message': 'The active task run has aborted.',
            'stderr': filtered_stderr
        })

    return JsonResponse(response_data)