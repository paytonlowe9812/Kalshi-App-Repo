from fastapi import APIRouter
from backend.models import LicenseValidate
from backend.license import validate_license, get_license_status

router = APIRouter(prefix="/api/license", tags=["license"])


@router.post("/validate")
async def validate(data: LicenseValidate):
    result = await validate_license(data.key)
    return result


@router.get("/status")
def status():
    return get_license_status()
