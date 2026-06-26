from fastapi import APIRouter, HTTPException

from app.schemas.products import AkkProduct
from app.services.product_service import ProductService

router = APIRouter(prefix="/akk-products", tags=["akk-products"])
product_service = ProductService()


@router.get("", response_model=list[AkkProduct])
def list_products() -> list[AkkProduct]:
    return product_service.list_products()


@router.get("/{product_id}", response_model=AkkProduct)
def get_product(product_id: str) -> AkkProduct:
    product = product_service.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
