from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # URLs de colegios
    path('colegios/', views.lista_colegios, name='lista_colegios'),
    path('colegios/nuevo/', views.registrar_colegio, name='registrar_colegio'),
    path('colegios/<int:pk>/editar/', views.editar_colegio, name='editar_colegio'),
    path('colegios/<int:pk>/eliminar/',
         views.eliminar_colegio, name='eliminar_colegio'),

    # URLs de usuarios
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/nuevo/', views.registrar_usuario, name='registrar_usuario'),
    path('usuarios/editar/<int:pk>/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/eliminar/<int:pk>/',
         views.eliminar_usuario, name='eliminar_usuario'),
    path('usuarios/toggle/<int:pk>/',
         views.toggle_usuario_estado, name='toggle_usuario'),

    # URLs de estudiantes
    path('estudiantes/', views.lista_estudiantes, name='lista_estudiantes'),
    path('buscar_estudiantes/', views.buscar_estudiantes,
         name='buscar_estudiantes'),
    path('estudiantes/nuevo/', views.registrar_estudiante,
         name='registrar_estudiante'),
    path('estudiantes/<int:pk>/', views.detalle_estudiante,
         name='detalle_estudiante'),
    path('estudiantes/<int:pk>/editar/',
         views.editar_estudiante, name='editar_estudiante'),
    path('estudiantes/<int:pk>/eliminar/',
         views.eliminar_estudiante, name='eliminar_estudiante'),
    path('estudiantes/carga-masiva/', views.carga_masiva_estudiantes,
         name='carga_masiva_estudiantes'),
    path('estudiantes/descargar-plantilla/',
         views.descargar_plantilla, name='descargar_plantilla'),
    path('estudiantes/descargar-log-errores/',
         views.descargar_log_errores, name='descargar_log_errores'),

    # URLs de atrasos
    path('atrasos/', views.lista_atrasos, name='lista_atrasos'),
    path('atrasos/nuevo/', views.registrar_atraso, name='registrar_atraso'),
    path('colegios/toggle/<int:pk>/',
         views.toggle_colegio_estado, name='toggle_colegio'),

    # URLs de reportes
    path('reportes/', views.reportes, name='reportes'),
    path('reportes/atrasos-por-estudiante/', views.reporte_atrasos_por_estudiante,
         name='reporte_atrasos_por_estudiante'),
    path('reportes/atrasos-por-curso/', views.reporte_atrasos_por_curso,
         name='reporte_atrasos_por_curso'),
    path('reportes/atrasos-por-fecha/', views.reporte_atrasos_por_fecha,
         name='reporte_atrasos_por_fecha'),
    path('reportes/exportar/<str:tipo_reporte>/',
         views.exportar_reporte_excel, name='exportar_reporte_excel'),

    # URLs de dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
]
