from django.db import models
from django.core.validators import RegexValidator

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


class Estudiante(models.Model):
    rut = models.CharField(
        max_length=12,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{1,2}\.\d{3}\.\d{3}-[\dkK]$',
                message='El RUT debe tener el formato XX.XXX.XXX-X'
            )
        ],
        help_text='Formato: XX.XXX.XXX-X'
    )
    nombre = models.CharField(max_length=100)
    curso = models.CharField(max_length=20, choices=CURSOS_CHILE)
    email1 = models.EmailField(verbose_name='Email Principal')
    email2 = models.EmailField(
        verbose_name='Email Secundario', blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} - {self.rut} - {self.curso}"

    class Meta:
        verbose_name = 'Estudiante'
        verbose_name_plural = 'Estudiantes'
        ordering = ['nombre']


class Atraso(models.Model):
    estudiante = models.ForeignKey(
        Estudiante, on_delete=models.CASCADE, related_name='atrasos')
    curso = models.CharField(max_length=20, choices=CURSOS_CHILE)
    fecha = models.DateField(auto_now_add=True)
    hora = models.TimeField(auto_now_add=True)
    justificacion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.estudiante.nombre} - {self.fecha} {self.hora}"

    class Meta:
        verbose_name = 'Atraso'
        verbose_name_plural = 'Atrasos'
        ordering = ['-fecha', '-hora']
