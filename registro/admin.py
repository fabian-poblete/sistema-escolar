from django.contrib import admin
from .models import Estudiante, Atraso


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ('rut', 'nombre', 'curso', 'email1')
    search_fields = ('rut', 'nombre', 'curso')
    list_filter = ('curso',)


@admin.register(Atraso)
class AtrasoAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'curso', 'fecha', 'hora')
    list_filter = ('curso', 'fecha')
    search_fields = ('estudiante__nombre', 'estudiante__rut', 'curso')
    date_hierarchy = 'fecha'
