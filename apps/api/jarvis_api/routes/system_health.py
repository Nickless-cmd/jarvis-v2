import shutil
import psutil
from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/system/health")
def system_health() -> dict:
    cpu_pct = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = shutil.disk_usage("/")
    return {
        "cpu_pct": round(cpu_pct, 1),
        "ram_pct": round(mem.percent, 1),
        "disk_free_mb": round(disk.free / (1024 * 1024), 0),
    }
