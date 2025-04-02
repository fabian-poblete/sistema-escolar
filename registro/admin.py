from django.contrib import admin
from .models import Estudiante, Atraso, Colegio, PerfilUsuario


@admin.register(Colegio)
class ColegioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'email', 'telefono', 'activo')
    search_fields = ('nombre', 'rut', 'email')
    list_filter = ('activo',)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'colegio', 'cargo', 'activo')
    search_fields = ('usuario__username', 'colegio__nombre', 'cargo')
    list_filter = ('colegio', 'cargo', 'activo')


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ('rut', 'nombre', 'curso', 'email_principal', 'colegio')
    search_fields = ('rut', 'nombre', 'curso')
    list_filter = ('curso', 'colegio', 'activo')


@admin.register(Atraso)
class AtrasoAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'curso', 'fecha', 'hora', 'registrado_por')
    list_filter = ('curso', 'fecha', 'estudiante__colegio')
    search_fields = ('estudiante__nombre', 'estudiante__rut', 'curso')
    date_hierarchy = 'fecha'
