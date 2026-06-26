from app.repositories.mock_repository import MockRepository
from app.schemas.products import AkkProduct


class ProductService:
    def __init__(self, repository: MockRepository | None = None) -> None:
        self.repository = repository or MockRepository()

    def list_products(self) -> list[AkkProduct]:
        return [AkkProduct.model_validate(item) for item in self.repository.get_products()]

    def get_product(self, product_id: str) -> AkkProduct | None:
        for product in self.repository.get_products():
            if product["productId"] == product_id:
                return AkkProduct.model_validate(product)
        return None
