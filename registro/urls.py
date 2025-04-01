from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('estudiantes/', views.lista_estudiantes, name='lista_estudiantes'),
    path('estudiantes/nuevo/', views.nuevo_estudiante, name='nuevo_estudiante'),
    path('estudiantes/<int:pk>/', views.detalle_estudiante,
         name='detalle_estudiante'),
    path('estudiantes/<int:pk>/editar/',
         views.editar_estudiante, name='editar_estudiante'),
    path('estudiantes/<int:pk>/eliminar/',
         views.eliminar_estudiante, name='eliminar_estudiante'),
    path('atrasos/', views.lista_atrasos, name='lista_atrasos'),
    path('atrasos/nuevo/', views.registrar_atraso, name='registrar_atraso'),
    path('logout/', views.logout_view, name='logout'),
    path("carga-masiva/", views.carga_masiva_estudiantes,
         name="carga_masiva_estudiantes"),
    path("descargar-plantilla/", views.descargar_plantilla,
         name="descargar_plantilla"),
    path('buscar_estudiantes/', views.buscar_estudiantes,
         name='buscar_estudiantes'),
    path('descargar-log-errores/', views.descargar_log_errores,
         name='descargar_log_errores'),
]
