import { ProductDetail } from "@/components/product/product-detail";
import { getAkkProduct } from "@/lib/api";

export default async function ProductDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const product = await getAkkProduct(id);

  return <ProductDetail product={product} />;
}
