import pyinstaller_versionfile

from app import VERSION, PRODUCT_NAME, COMPANY_NAME

pyinstaller_versionfile.create_versionfile(
    output_file="../../version.py",
    version=VERSION,
    company_name=COMPANY_NAME,
    file_description=PRODUCT_NAME,
    internal_name=PRODUCT_NAME,
    legal_copyright=f"© {COMPANY_NAME}",
    original_filename=f"{PRODUCT_NAME}.exe",
    product_name=PRODUCT_NAME,
)
