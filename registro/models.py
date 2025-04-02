from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, time

# Definir cursos con secciones "A" y "B"
CURSOS_CHILE = [
    (f"{nivel} {letra}", f"{nivel} {letra}")
    for nivel in [
        "Pre-Kínder", "Kínder",
        "1° Básico", "2° Básico", "3° Básico", "4° Básico",
        "5° Básico", "6° Básico", "7° Básico", "8° Básico",
        "1° Medio", "2° Medio", "3° Medio", "4° Medio"
    ]
    for letra in ["A", "B"]
]


class Colegio(models.Model):
    nombre = models.CharField(max_length=200)
    rut = models.CharField(max_length=20, unique=True)
    direccion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20)
    email = models.EmailField()
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.rut})"

    class Meta:
        verbose_name = "Colegio"
        verbose_name_plural = "Colegios"


class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE)
    cargo = models.CharField(max_length=100)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.colegio.nombre}"

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"


class Estudiante(models.Model):
    colegio = models.ForeignKey(
        Colegio, on_delete=models.CASCADE, related_name='estudiantes')
    rut = models.CharField(max_length=12, unique=True,
                           help_text='Formato: 12345678-9')
    nombre = models.CharField(max_length=200)
    curso = models.CharField(max_length=50, choices=CURSOS_CHILE)
    email_principal = models.EmailField()
    email_secundario = models.EmailField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} - {self.curso}"

    class Meta:
        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"
        ordering = ['curso', 'nombre']
        unique_together = ['colegio', 'rut']
        unique_together = ['colegio', 'email_principal']


class Atraso(models.Model):
    estudiante = models.ForeignKey(
        Estudiante, on_delete=models.CASCADE, related_name='atrasos')
    fecha = models.DateField()
    hora = models.TimeField()
    curso = models.CharField(max_length=50)
    motivo = models.TextField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.estudiante.nombre} - {self.fecha} {self.hora}"

    def clean(self):
        # Validar que la fecha no sea futura
        if self.fecha > timezone.now().date():
            raise ValidationError('La fecha no puede ser futura')

        # Asegurarse de que la hora esté establecida
        if self.hora is None:
            raise ValidationError('La hora es requerida')

    class Meta:
        verbose_name = "Atraso"
        verbose_name_plural = "Atrasos"
        ordering = ['-fecha', '-hora']
