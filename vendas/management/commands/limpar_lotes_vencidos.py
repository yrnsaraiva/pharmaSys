# management/commands/limpar_lotes_vencidos.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from vendas.models import Lote


class Command(BaseCommand):
    help = 'Remove do estoque todos os lotes vencidos'

    def handle(self, *args, **options):
        hoje = timezone.now().date()

        # Buscar lotes vencidos com estoque
        lotes_vencidos = Lote.objects.filter(
            data_validade__lt=hoje,
            quantidade_disponivel__gt=0
        )

        total_lotes = lotes_vencidos.count()
        total_unidades = sum(lote.quantidade_disponivel for lote in lotes_vencidos)

        # Zerar os lotes vencidos
        for lote in lotes_vencidos:
            lote.quantidade_disponivel = 0
            lote.nr_caixas = 0
            lote.nr_carteiras = 0
            lote.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ {total_lotes} lotes vencidos removidos do estoque. "
                f"Total de {total_unidades} unidades bloqueadas para venda."
            )
        )