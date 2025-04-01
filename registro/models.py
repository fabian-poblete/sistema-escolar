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
    # El RUT almacenado será sin puntos ni guion
    rut = models.CharField(
        max_length=10,  # El tamaño será 10, ya que no tendrá los puntos ni el guion
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{7,8}-[\dkK]$',  # Solo números y guion al final
                message='El RUT debe tener el formato XXXXXXXXX-X o XXXXXXXXX-K'
            )
        ],
        help_text='Formato: XXXXXXXXX-X o XXXXXXXXX-K (sin puntos ni guion)'
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

    # Limpiar el RUT antes de guardarlo (eliminando puntos y guion)
    def save(self, *args, **kwargs):
        # Eliminar puntos y guion del RUT
        self.rut = self.rut.replace('.', '').replace('-', '')
        super(Estudiante, self).save(*args, **kwargs)


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
