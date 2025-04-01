from django.http import JsonResponse
from .models import Estudiante  # Asegúrate de importar el modelo correcto
from .models import Atraso  # Asumiendo que tienes el modelo Atraso
from django.shortcuts import render
from django.http import HttpResponse
from .models import Estudiante
from django.shortcuts import render, redirect
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from django.core.mail import send_mail
from django.conf import settings
from .models import Estudiante, Atraso
from .forms import EstudianteForm, AtrasoForm
from datetime import datetime
import logging
import json
from django.urls import reverse

logger = logging.getLogger(__name__)


def home(request):
    return render(request, 'registro/home.html')


def logout_view(request):
    auth_logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('home')


@login_required
def lista_estudiantes(request):
    estudiantes = Estudiante.objects.all()

    # Filtrar por nombre
    nombre = request.GET.get('nombre', '')
    if nombre:
        estudiantes = estudiantes.filter(nombre__icontains=nombre)

    # Filtrar por RUT
    rut = request.GET.get('rut', '')
    if rut:
        estudiantes = estudiantes.filter(rut__icontains=rut)

    # Filtrar por curso
    curso = request.GET.get('curso', '')
    if curso:
        estudiantes = estudiantes.filter(curso__icontains=curso)

    return render(request, 'registro/lista_estudiantes.html', {
        'estudiantes': estudiantes,
        'nombre': nombre,
        'rut': rut,
        'curso': curso,
    })


@login_required
def nuevo_estudiante(request):
    if request.method == 'POST':
        form = EstudianteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Estudiante registrado exitosamente.')
            return redirect('lista_estudiantes')
    else:
        form = EstudianteForm()
    return render(request, 'registro/estudiante_form.html', {'form': form, 'titulo': 'Nuevo Estudiante'})


@login_required
def editar_estudiante(request, pk):
    estudiante = get_object_or_404(Estudiante, pk=pk)
    if request.method == 'POST':
        form = EstudianteForm(request.POST, instance=estudiante)
        if form.is_valid():
            form.save()
            messages.success(request, 'Estudiante actualizado exitosamente.')
            return redirect('lista_estudiantes')
    else:
        form = EstudianteForm(instance=estudiante)
    return render(request, 'registro/estudiante_form.html', {'form': form, 'titulo': 'Editar Estudiante'})


@login_required
def eliminar_estudiante(request, pk):
    estudiante = get_object_or_404(Estudiante, pk=pk)
    if request.method == 'POST':
        estudiante.delete()
        messages.success(request, 'Estudiante eliminado exitosamente.')
        return redirect('lista_estudiantes')
    return render(request, 'registro/estudiante_confirmar_eliminacion.html', {'estudiante': estudiante})


@login_required
def registrar_atraso(request):
    if request.method == 'POST':
        form = AtrasoForm(request.POST)
        if form.is_valid():
            try:
                atraso = Atraso()
                atraso.estudiante = form.cleaned_data['estudiante_id']
                atraso.curso = atraso.estudiante.curso
                atraso.justificacion = form.cleaned_data['justificacion']
                atraso.save()

                # Intentar enviar notificación por email
                try:
                    estudiante = atraso.estudiante
                    subject = f'Atraso registrado - {estudiante.nombre}'
                    message = f"""
                    Se ha registrado un atraso para el estudiante {estudiante.nombre}:
                    Fecha: {atraso.fecha}
                    Hora: {atraso.hora}
                    Curso: {atraso.curso}
                    Justificación: {
                        atraso.justificacion or 'Sin justificación'}
                    """
                    send_mail(
                        subject,
                        message,
                        settings.EMAIL_HOST_USER,
                        [estudiante.email1],
                        fail_silently=False,
                    )
                    if estudiante.email2:
                        send_mail(
                            subject,
                            message,
                            settings.EMAIL_HOST_USER,
                            [estudiante.email2],
                            fail_silently=False,
                        )
                    messages.success(
                        request, 'Atraso registrado y notificación enviada.')
                except Exception as e:
                    logger.error(f"Error al enviar email: {str(e)}")
                    messages.warning(
                        request, 'Atraso registrado pero no se pudo enviar la notificación por email.')

                return redirect('lista_atrasos')
            except Exception as e:
                messages.error(
                    request, f'Error al registrar el atraso: {str(e)}')
        else:
            messages.error(
                request, 'Por favor, corrija los errores en el formulario.')
    else:
        form = AtrasoForm()
    return render(request, 'registro/atraso_form.html', {'form': form})


@login_required
def lista_atrasos(request):
    atrasos = Atraso.objects.all()

    # Obtener parámetros de búsqueda desde la URL
    fecha = request.GET.get('fecha', '')
    estudiante = request.GET.get('estudiante', '')
    curso = request.GET.get('curso', '')

    # Filtrar según los parámetros de búsqueda
    if fecha:
        atrasos = atrasos.filter(fecha__icontains=fecha)
    if estudiante:
        atrasos = atrasos.filter(estudiante__nombre__icontains=estudiante)
    if curso:
        atrasos = atrasos.filter(curso__icontains=curso)

    return render(request, 'registro/lista_atrasos.html', {
        'atrasos': atrasos,
        'fecha': fecha,
        'estudiante': estudiante,
        'curso': curso,
    })


@login_required
def detalle_estudiante(request, pk):
    estudiante = get_object_or_404(Estudiante, pk=pk)
    atrasos = estudiante.atrasos.all()
    return render(request, 'registro/detalle_estudiante.html', {
        'estudiante': estudiante,
        'atrasos': atrasos
    })


# Vista para descargar la plantilla Excel


def descargar_plantilla(request):
    # Definir las columnas necesarias
    columnas = ["RUT", "Nombre", "Curso",
                "Email Principal", "Email Secundario"]

    # Crear un DataFrame vacío con las columnas
    df = pd.DataFrame(columns=columnas)

    # Crear la respuesta HTTP con el archivo Excel
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="plantilla_estudiantes.xlsx"'

    # Convertir el DataFrame a un archivo Excel y enviarlo en la respuesta
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)

    return response

# Vista para la carga masiva de estudiantes


def descargar_log_errores(request):
    # Obtener los errores de la sesión
    errores = request.session.get('errores_carga_masiva', [])
    estudiantes_exitosos = request.session.get('estudiantes_exitosos', 0)
    total_estudiantes = request.session.get('total_estudiantes', 0)

    # Crear el contenido del log
    log_content = "Reporte de Errores en Carga Masiva\n"
    log_content += "================================\n\n"
    log_content += f"Total de estudiantes procesados: {total_estudiantes}\n"
    log_content += f"Estudiantes registrados exitosamente: {estudiantes_exitosos}\n"
    log_content += f"Errores encontrados: {len(errores)}\n\n"
    log_content += "Detalle de errores:\n"
    log_content += "-----------------\n"
    for error in errores:
        log_content += f"- {error}\n"

    # Crear la respuesta HTTP con el archivo de log
    response = HttpResponse(log_content, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="errores_carga_masiva.txt"'

    # Limpiar los datos de la sesión después de descargar
    request.session.pop('errores_carga_masiva', None)
    request.session.pop('estudiantes_exitosos', None)
    request.session.pop('total_estudiantes', None)

    return response


def carga_masiva_estudiantes(request):
    if request.method == "POST":
        file = request.FILES.get("file")

        if not file:
            messages.error(request, "No se seleccionó ningún archivo.")
            return redirect("lista_estudiantes")

        try:
            df = pd.read_excel(file)  # Leer el archivo Excel

            # Validar que el archivo contenga las columnas correctas
            columnas_requeridas = {"RUT", "Nombre", "Curso",
                                   "Email Principal", "Email Secundario"}
            if not columnas_requeridas.issubset(df.columns):
                messages.error(
                    request, "El archivo debe contener las columnas: RUT, Nombre, Curso, Email Principal, Email Secundario")
                return redirect("lista_estudiantes")

            # Lista para almacenar los errores
            errores = []
            estudiantes_exitosos = 0

            # Insertar los datos en la base de datos
            for index, row in df.iterrows():
                try:
                    Estudiante.objects.create(
                        rut=row["RUT"],
                        nombre=row["Nombre"],
                        curso=row["Curso"],
                        email1=row["Email Principal"],
                        email2=row.get("Email Secundario", "")
                    )
                    estudiantes_exitosos += 1
                except Exception as e:
                    # Crear un mensaje de error amigable
                    mensaje_error = f"Fila {index + 2}: "
                    if "UNIQUE constraint failed" in str(e):
                        mensaje_error += f"El RUT {row['RUT']} ya está registrado en el sistema."
                    else:
                        mensaje_error += f"Error al procesar el estudiante {row['Nombre']} con RUT {row['RUT']}."
                    errores.append(mensaje_error)

            # Si hay errores, guardar en la sesión y mostrar mensaje con link
            if errores:
                request.session['errores_carga_masiva'] = errores
                request.session['estudiantes_exitosos'] = estudiantes_exitosos
                request.session['total_estudiantes'] = len(df)

                # Crear el mensaje con el link
                url_descarga = reverse('descargar_log_errores')
                mensaje = f"Se procesaron {estudiantes_exitosos} estudiantes. Se encontraron {len(errores)} errores. "
                mensaje += f'<a href="{url_descarga}" class="alert-link">Descargar reporte de errores</a>.'

                messages.warning(request, mensaje, extra_tags='safe')
            else:
                messages.success(
                    request, f"Se procesaron exitosamente {estudiantes_exitosos} estudiantes.")

        except Exception as e:
            messages.error(
                request, "Ocurrió un error al procesar el archivo. Por favor, verifique el formato del archivo.")

        return redirect("lista_estudiantes")

    return redirect("lista_estudiantes")


def buscar_estudiantes(request):
    query = request.GET.get('q', '')
    if query:
        estudiantes = Estudiante.objects.filter(
            nombre__icontains=query
        ) | Estudiante.objects.filter(rut__icontains=query)
        resultados = [{'id': estudiante.id, 'nombre': estudiante.nombre,
                       'rut': estudiante.rut} for estudiante in estudiantes]
    else:
        resultados = []

    return JsonResponse(resultados, safe=False)
