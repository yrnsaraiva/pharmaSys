from django.db import models


class Fornecedor(models.Model):
    nome = models.CharField(max_length=100)
    pessoa_de_contacto = models.CharField(max_length=100)
    nuit = models.CharField(max_length=18, unique=True)
    telefone = models.CharField(max_length=15)
    email = models.EmailField(null=True, blank=True)
    endereco = models.TextField()
    status = models.BooleanField()

    def __str__(self):
        return f'{self.nome} {self.nuit}'

