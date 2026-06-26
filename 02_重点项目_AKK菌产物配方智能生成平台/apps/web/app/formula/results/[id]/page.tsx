import { FormulaResultDetail } from "@/components/formula/formula-result-detail";
import { ButtonLink } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { getAkkProducts, getFormulaResult } from "@/lib/api";

export default async function FormulaResultPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const [result, products] = await Promise.all([getFormulaResult(id), getAkkProducts()]);

    return <FormulaResultDetail products={products} result={result} />;
  } catch {
    return (
      <Card>
        <CardTitle>没有找到这个方案</CardTitle>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          当前方案可能来自旧的临时生成记录，或者后端服务重启后没有读取到对应结果。你可以返回方案库查看已有方案，
          也可以回到设计台重新生成一份方案。
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <ButtonLink href="/" variant="primary">返回设计台</ButtonLink>
          <ButtonLink href="/formula/results" variant="secondary">查看方案库</ButtonLink>
        </div>
      </Card>
    );
  }
}
