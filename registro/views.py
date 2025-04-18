from django.shortcuts import render
from .models import Estudiante, Atraso
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
import json
import logging
import pandas as pd

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth import login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from .forms import ColegioForm, RegistroUsuarioForm, EstudianteForm, AtrasoForm
from .models import Colegio, PerfilUsuario, Estudiante, Atraso


logger = logging.getLogger(__name__)


def get_colegio_from_user(user):
    """Obtiene el colegio asociado al usuario a través de su perfil."""
    try:
        return user.perfilusuario.colegio
    except PerfilUsuario.DoesNotExist:
        return None


@login_required
def home(request):
    # Obtener el colegio del usuario
    colegio = get_colegio_from_user(request.user)

    if colegio:
        total_estudiantes = Estudiante.objects.filter(colegio=colegio).count()
        total_atrasos = Atraso.objects.filter(
            estudiante__colegio=colegio).count()
    else:
        total_estudiantes = Estudiante.objects.count()
        total_atrasos = Atraso.objects.count()

    context = {
        'total_estudiantes': total_estudiantes,
        'total_atrasos': total_atrasos,
    }
    return render(request, 'registro/home.html', context)


def logout_view(request):
    auth_logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('home')


@login_required
def lista_estudiantes(request):
    # Obtener el colegio del usuario
    colegio = get_colegio_from_user(request.user)

    # Filtrar estudiantes por colegio si existe
    estudiantes = Estudiante.objects.select_related('colegio').all()
    if colegio and not request.user.is_superuser:
        estudiantes = estudiantes.filter(colegio=colegio)

    # Aplicar filtros de búsqueda
    nombre = request.GET.get('nombre')
    rut = request.GET.get('rut')
    curso = request.GET.get('curso')
    colegio_busqueda = request.GET.get('colegio')

    if nombre:
        estudiantes = estudiantes.filter(nombre__icontains=nombre)
    if rut:
        estudiantes = estudiantes.filter(rut__icontains=rut)
    if curso:
        estudiantes = estudiantes.filter(curso__icontains=curso)
    if colegio_busqueda and request.user.is_superuser:
        estudiantes = estudiantes.filter(
            colegio__nombre__icontains=colegio_busqueda)

    # Paginación
    paginator = Paginator(estudiantes, 10)
    page = request.GET.get('page')
    estudiantes = paginator.get_page(page)

    return render(request, 'registro/lista_estudiantes.html', {
        'estudiantes': estudiantes,
        'nombre': nombre,
        'rut': rut,
        'curso': curso,
        'colegio': colegio_busqueda
    })


@login_required
def registrar_estudiante(request):
    if request.method == 'POST':
        form = EstudianteForm(request.POST, user=request.user)
        if form.is_valid():
            estudiante = form.save()
            messages.success(request, 'Estudiante registrado exitosamente.')
            return redirect('lista_estudiantes')
    else:
        form = EstudianteForm(user=request.user)

    return render(request, 'registro/estudiante_form.html', {
        'form': form,
        'titulo': 'Nuevo Estudiante'
    })


@login_required
def editar_estudiante(request, pk):
    estudiante = get_object_or_404(Estudiante, pk=pk)

    # Verificar que el usuario tenga permiso para editar este estudiante
    if not request.user.is_superuser:
        colegio = get_colegio_from_user(request.user)
        if estudiante.colegio != colegio:
            messages.error(
                request, 'No tiene permiso para editar este estudiante.')
            return redirect('lista_estudiantes')

    if request.method == 'POST':
        form = EstudianteForm(
            request.POST, instance=estudiante, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Estudiante actualizado exitosamente.')
            return redirect('lista_estudiantes')
    else:
        form = EstudianteForm(instance=estudiante, user=request.user)

    return render(request, 'registro/estudiante_form.html', {
        'form': form,
        'titulo': 'Editar Estudiante'
    })


@login_required
def eliminar_estudiante(request, pk):
    estudiante = get_object_or_404(Estudiante, pk=pk)

    # Verificar que el usuario tenga permiso para eliminar este estudiante
    if not request.user.is_superuser:
        colegio = get_colegio_from_user(request.user)
        if estudiante.colegio != colegio:
            messages.error(
                request, 'No tiene permiso para eliminar este estudiante.')
            return redirect('lista_estudiantes')

    if request.method == 'POST':
        estudiante.delete()
        messages.success(request, 'Estudiante eliminado exitosamente.')
        return redirect('lista_estudiantes')

    return render(request, 'registro/estudiante_confirmar_eliminacion.html', {
        'estudiante': estudiante
    })


@login_required
def registrar_atraso(request):
    if request.method == 'POST':
        estudiante_id = request.POST.get('estudiante')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if not estudiante_id:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Debe seleccionar un estudiante.'
                })
            else:
                messages.error(request, 'Debe seleccionar un estudiante.')
                return redirect('registrar_atraso')

        try:
            estudiante = Estudiante.objects.get(id=estudiante_id)

            # Verificar permisos
            if not request.user.is_superuser and estudiante.colegio != request.user.colegio:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': 'No tiene permiso para registrar atrasos para este estudiante.'
                    })
                else:
                    messages.error(
                        request, 'No tiene permiso para registrar atrasos para este estudiante.')
                    return redirect('registrar_atraso')

            # Obtener fecha y hora
            fecha = request.POST.get('fecha') or timezone.now().date()
            hora = request.POST.get('hora') or timezone.now().time()

            # Si se proporciona fecha, convertir de string a date
            if fecha:
                try:
                    fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
                except ValueError:
                    fecha = timezone.now().date()
            else:
                fecha = timezone.now().date()

            # Si se proporciona hora, convertir de string a time
            if hora:
                try:
                    hora = datetime.strptime(hora, '%H:%M').time()
                except ValueError:
                    hora = timezone.now().time()
            else:
                hora = timezone.now().time()

            # Crear el registro de atraso
            atraso = Atraso.objects.create(
                estudiante=estudiante,
                fecha=fecha,
                hora=hora,
                motivo=request.POST.get('motivo', ''),
                registrado_por=request.user
            )

            # Mensaje base de éxito
            success_message = f'Atraso registrado correctamente para {estudiante.nombre}.'
            email_status = ''

            # Enviar correo de notificación a los apoderados
            if estudiante.email_principal or estudiante.email_secundario:
                recipients = []
                if estudiante.email_principal:
                    recipients.append(estudiante.email_principal)
                if estudiante.email_secundario:
                    recipients.append(estudiante.email_secundario)

                # Enviar el correo
                if recipients:
                    try:
                        send_mail(
                            subject=f'Notificación de Atraso - {estudiante.colegio.nombre}',
                            message=f"""
                                    Estimado/a Apoderado/a,

                                    Le informamos que el/la estudiante {estudiante.nombre} ha sido registrado/a con un atraso a clases el día {atraso.fecha.strftime('%d/%m/%Y')} a las {atraso.hora.strftime('%H:%M')}.

                                    Justificación del atraso: {atraso.motivo if atraso.motivo else "No se ha indicado justificación."}

                                    Este mensaje ha sido enviado desde el sistema de registro de atrasos del colegio {estudiante.colegio.nombre}.

                                    Si tiene dudas o requiere más información, no dude en contactarnos.

                                    Atentamente,
                                    Equipo de Convivencia Escolar
                                    {estudiante.colegio.nombre}
                                    """,
                            from_email=settings.EMAIL_HOST_USER,
                            recipient_list=recipients,
                            fail_silently=False,
                        )
                        email_status = 'Notificación enviada a los apoderados.'
                    except Exception as e:
                        email_status = f'Error al enviar notificación: {str(e)}'
                else:
                    email_status = 'No se encontraron correos de apoderados para enviar la notificación.'

            # Construir mensaje completo
            full_message = success_message
            if email_status:
                full_message = f"{success_message} {email_status}"

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': full_message,
                    'atraso': {
                        'id': atraso.id,
                        'fecha': atraso.fecha.strftime('%d/%m/%Y'),
                        'hora': atraso.hora.strftime('%H:%M'),
                        'estudiante': {
                            'id': estudiante.id,
                            'nombre': estudiante.nombre,
                            'curso': estudiante.curso
                        }
                    }
                })
            else:
                messages.success(request, full_message)
                return redirect('registrar_atraso')

        except Estudiante.DoesNotExist:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Estudiante no encontrado.'
                })
            else:
                messages.error(request, 'Estudiante no encontrado.')
                return redirect('registrar_atraso')
        except Exception as e:
            error_message = f'Error al registrar el atraso: {str(e)}'
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': error_message
                })
            else:
                messages.error(request, error_message)
                return redirect('registrar_atraso')

    return render(request, 'registro/atraso_form.html', {'title': 'Registrar Atraso'})


@login_required
def buscar_estudiantes(request):
    """Vista para buscar estudiantes mediante AJAX"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse([], safe=False)

    # Obtener colegio del usuario si no es superusuario
    colegio = None
    if not request.user.is_superuser and hasattr(request.user, 'perfilusuario'):
        colegio = request.user.perfilusuario.colegio

    # Filtrar estudiantes
    estudiantes = Estudiante.objects.filter(
        Q(nombre__icontains=query) | Q(rut__icontains=query)
    )

    # Si no es superusuario, filtrar por colegio
    if colegio and not request.user.is_superuser:
        estudiantes = estudiantes.filter(colegio=colegio)

    # Limitar resultados
    estudiantes = estudiantes[:20]

    # Preparar datos para JSON
    results = []
    for estudiante in estudiantes:
        results.append({
            'id': estudiante.id,
            'nombre': estudiante.nombre,
            'rut': estudiante.rut,
            'curso': estudiante.curso
        })

    return JsonResponse(results, safe=False)


@login_required
def lista_atrasos(request):
    # Iniciar con todos los atrasos y usar select_related para optimizar consultas
    atrasos = Atraso.objects.select_related(
        'estudiante', 'estudiante__colegio').all()

    # Filtrar por colegio solo si el usuario no es superusuario
    colegio = get_colegio_from_user(request.user)
    if colegio and not request.user.is_superuser:
        atrasos = atrasos.filter(estudiante__colegio=colegio)

    # Aplicar filtros
    fecha = request.GET.get('fecha')
    estudiante = request.GET.get('estudiante')
    curso = request.GET.get('curso')
    colegio_busqueda = request.GET.get('colegio')

    if fecha:
        try:
            # La fecha viene en formato YYYY-MM-DD del input type="date"
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
            atrasos = atrasos.filter(fecha=fecha_obj)
        except ValueError:
            messages.error(request, 'Formato de fecha inválido')

    if estudiante:
        atrasos = atrasos.filter(
            Q(estudiante__nombre__icontains=estudiante) |
            Q(estudiante__rut__icontains=estudiante)
        )

    if curso:
        atrasos = atrasos.filter(estudiante__curso__icontains=curso)

    if colegio_busqueda and request.user.is_superuser:
        atrasos = atrasos.filter(
            estudiante__colegio__nombre__icontains=colegio_busqueda)

    # Paginación
    paginator = Paginator(atrasos, 10)
    page = request.GET.get('page')
    atrasos = paginator.get_page(page)

    return render(request, 'registro/lista_atrasos.html', {
        'atrasos': atrasos,
        'fecha': fecha,
        'estudiante': estudiante,
        'curso': curso,
        'colegio': colegio_busqueda,
        'is_superuser': request.user.is_superuser
    })


@login_required
def detalle_estudiante(request, pk):
    estudiante = get_object_or_404(Estudiante, pk=pk)

    # Verificar que el usuario tenga permiso para ver este estudiante
    if not request.user.is_superuser:
        colegio = get_colegio_from_user(request.user)
        if estudiante.colegio != colegio:
            messages.error(
                request, 'No tiene permiso para ver este estudiante.')
            return redirect('lista_estudiantes')

    return render(request, 'registro/detalle_estudiante.html', {
        'estudiante': estudiante
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


@login_required
def descargar_log_errores(request):
    errores = request.session.get('errores_carga', [])
    if not errores:
        messages.error(request, 'No hay errores para descargar.')
        return redirect('lista_estudiantes')

    # Crear contenido del log
    contenido = "Reporte de Errores en Carga Masiva\n"
    contenido += "================================\n\n"
    contenido += f"Total de errores encontrados: {len(errores)}\n\n"
    contenido += "Detalle de errores:\n"
    contenido += "-----------------\n"
    for error in errores:
        contenido += f"{error}\n"

    # Limpiar errores de la sesión
    del request.session['errores_carga']

    # Crear respuesta
    response = HttpResponse(contenido, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="errores_carga.txt"'
    return response


@login_required
def carga_masiva_estudiantes(request):
    # Obtener el colegio del usuario
    colegio = get_colegio_from_user(request.user)

    if not colegio:
        messages.error(
            request, 'No tiene un colegio asignado para realizar esta operación.')
        return redirect('lista_estudiantes')

    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        archivo = request.FILES['archivo_excel']
        try:
            df = pd.read_excel(archivo)
            errores = []
            estudiantes_procesados = 0

            # Verificar columnas requeridas
            columnas_requeridas = ["RUT", "Nombre", "Curso",
                                   "Email Principal", "Email Secundario"]
            columnas_faltantes = [
                col for col in columnas_requeridas if col not in df.columns]
            if columnas_faltantes:
                raise ValueError(
                    f"Faltan las siguientes columnas: {', '.join(columnas_faltantes)}")

            for _, row in df.iterrows():
                try:
                    Estudiante.objects.create(
                        colegio=colegio,
                        rut=row["RUT"],
                        nombre=row["Nombre"],
                        curso=row["Curso"],
                        email_principal=row["Email Principal"],
                        email_secundario=row["Email Secundario"]
                    )
                    estudiantes_procesados += 1
                except Exception as e:
                    errores.append(f"Error en fila {_ + 2}: {str(e)}")

            if errores:
                request.session['errores_carga'] = errores
                messages.warning(
                    request,
                    f'Se procesaron {estudiantes_procesados} estudiantes. Se encontraron {len(errores)} errores. '
                    f'<a href="{reverse("descargar_log_errores")}" class="alert-link">Descargar reporte de errores</a>',
                    extra_tags='safe'
                )
            else:
                messages.success(
                    request, f'Se procesaron exitosamente {estudiantes_procesados} estudiantes.')

        except Exception as e:
            messages.error(request, f'Error al procesar el archivo: {str(e)}')

        return redirect('lista_estudiantes')

    return render(request, 'registro/carga_masiva.html')


def es_superusuario(user):
    return user.is_superuser


@user_passes_test(es_superusuario)
def registrar_colegio(request):
    if request.method == 'POST':
        form = ColegioForm(request.POST)
        if form.is_valid():
            colegio = form.save()
            messages.success(request, 'Colegio registrado exitosamente.')
            return redirect('lista_colegios')
    else:
        form = ColegioForm()

    return render(request, 'registro/colegio_form.html', {'form': form})


@user_passes_test(es_superusuario)
def lista_colegios(request):
    colegios = Colegio.objects.all()

    # Búsqueda
    query = request.GET.get('q')
    if query:
        colegios = colegios.filter(
            Q(nombre__icontains=query) |
            Q(rut__icontains=query) |
            Q(email__icontains=query)
        )

    # Paginación
    paginator = Paginator(colegios, 10)
    page = request.GET.get('page')
    colegios = paginator.get_page(page)

    return render(request, 'registro/lista_colegios.html', {
        'colegios': colegios,
        'query': query
    })


@user_passes_test(es_superusuario)
def registrar_usuario(request):
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario registrado exitosamente.')
            return redirect('lista_usuarios')
    else:
        form = RegistroUsuarioForm()

    return render(request, 'registro/usuario_form.html', {'form': form})


@user_passes_test(es_superusuario)
def lista_usuarios(request):
    perfiles = PerfilUsuario.objects.select_related('usuario', 'colegio').all()

    # Búsqueda
    query = request.GET.get('q')
    if query:
        perfiles = perfiles.filter(
            Q(usuario__username__icontains=query) |
            Q(usuario__email__icontains=query) |
            Q(colegio__nombre__icontains=query)
        )

    # Paginación
    paginator = Paginator(perfiles, 10)
    page = request.GET.get('page')
    perfiles = paginator.get_page(page)

    return render(request, 'registro/lista_usuarios.html', {
        'perfiles': perfiles,
        'query': query
    })


@login_required
@user_passes_test(es_superusuario)
def editar_colegio(request, pk):
    colegio = get_object_or_404(Colegio, pk=pk)
    if request.method == 'POST':
        form = ColegioForm(request.POST, instance=colegio)
        if form.is_valid():
            form.save()
            messages.success(request, 'Colegio actualizado exitosamente.')
            return redirect('lista_colegios')
    else:
        form = ColegioForm(instance=colegio)
    return render(request, 'registro/colegio_form.html', {'form': form, 'colegio': colegio})


@login_required
@user_passes_test(es_superusuario)
def eliminar_colegio(request, pk):
    colegio = get_object_or_404(Colegio, pk=pk)
    if request.method == 'POST':
        colegio.delete()
        messages.success(request, 'Colegio eliminado exitosamente.')
        return redirect('lista_colegios')
    return render(request, 'registro/colegio_confirm_delete.html', {'colegio': colegio})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bienvenido, {user.username}!')
            return redirect('home')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    else:
        form = AuthenticationForm()

    return render(request, 'registration/login.html', {'form': form})


@login_required
@user_passes_test(es_superusuario)
def editar_usuario(request, pk):
    perfil = get_object_or_404(PerfilUsuario, pk=pk)
    usuario = perfil.usuario

    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            # Actualizar usuario
            usuario = form.save(commit=False)
            usuario.save()

            # Actualizar perfil
            perfil.colegio = form.cleaned_data['colegio']
            perfil.cargo = form.cleaned_data['cargo']
            perfil.save()

            messages.success(request, 'Usuario actualizado exitosamente.')
            return redirect('lista_usuarios')
    else:
        # Pre-poblar el formulario con los datos existentes
        initial_data = {
            'username': usuario.username,
            'email': usuario.email,
            'colegio': perfil.colegio,
            'cargo': perfil.cargo
        }
        form = RegistroUsuarioForm(instance=usuario, initial=initial_data)
        # Hacer los campos de contraseña opcionales para edición
        form.fields['password1'].required = False
        form.fields['password2'].required = False

    return render(request, 'registro/usuario_form.html', {
        'form': form,
        'titulo': 'Editar Usuario',
        'is_edit': True
    })


@login_required
@user_passes_test(es_superusuario)
def eliminar_usuario(request, pk):
    perfil = get_object_or_404(PerfilUsuario, pk=pk)
    if request.method == 'POST':
        usuario = perfil.usuario
        nombre_usuario = usuario.username  # Guardamos el nombre antes de eliminar
        usuario.delete()  # Esto también eliminará el perfil por la relación CASCADE
        messages.success(
            request, f'Usuario "{nombre_usuario}" eliminado exitosamente.')
        return redirect('lista_usuarios')

    return render(request, 'registro/usuario_confirm_delete.html', {
        'perfil': perfil,
        'titulo': 'Confirmar Eliminación'
    })


@login_required
@user_passes_test(es_superusuario)
def toggle_usuario_estado(request, pk):
    perfil = get_object_or_404(PerfilUsuario, pk=pk)
    usuario = perfil.usuario
    usuario.is_active = not usuario.is_active
    usuario.save()

    estado = "activado" if usuario.is_active else "suspendido"
    messages.success(
        request, f'Usuario "{usuario.username}" {estado} exitosamente.')
    return redirect('lista_usuarios')


@login_required
@user_passes_test(es_superusuario)
def toggle_colegio_estado(request, pk):
    colegio = get_object_or_404(Colegio, pk=pk)
    colegio.activo = not colegio.activo
    colegio.save()

    # También actualizar el estado de los usuarios asociados
    if not colegio.activo:
        PerfilUsuario.objects.filter(
            colegio=colegio).update(usuario__is_active=False)

    estado = "activado" if colegio.activo else "suspendido"
    messages.success(
        request, f'Colegio "{colegio.nombre}" {estado} exitosamente.')
    return redirect('lista_colegios')


@login_required
def reportes(request):
    colegio = get_colegio_from_user(request.user)

    # Obtener estadísticas generales
    if colegio:
        total_estudiantes = Estudiante.objects.filter(colegio=colegio).count()
        total_atrasos = Atraso.objects.filter(
            estudiante__colegio=colegio).count()
    else:
        total_estudiantes = Estudiante.objects.count()
        total_atrasos = Atraso.objects.count()

    # Datos para gráficos
    atrasos_por_fecha = Atraso.objects.filter(estudiante__colegio=colegio).values(
        'fecha').annotate(total=Count('id')).order_by('fecha')

    context = {
        'colegio': colegio,
        'total_estudiantes': total_estudiantes,
        'total_atrasos': total_atrasos,
        'atrasos_por_fecha': atrasos_por_fecha,
    }

    return render(request, 'registro/reportes.html', context)


@login_required
def reporte_atrasos_por_estudiante(request):
    """
    Genera un reporte de atrasos por estudiante.
    Permite filtrar por fecha, curso y estudiante.
    """
    colegio = get_colegio_from_user(request.user)

    # Obtener parámetros de filtrado
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    curso = request.GET.get('curso', '')
    estudiante_id = request.GET.get('estudiante', '')

    # Consulta base
    if colegio:
        atrasos = Atraso.objects.filter(estudiante__colegio=colegio)
    else:
        atrasos = Atraso.objects.all()

    # Aplicar filtros
    if fecha_inicio:
        atrasos = atrasos.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        atrasos = atrasos.filter(fecha__lte=fecha_fin)
    if curso:
        atrasos = atrasos.filter(curso=curso)
    if estudiante_id:
        atrasos = atrasos.filter(estudiante_id=estudiante_id)

    # Agrupar por estudiante
    estudiantes = Estudiante.objects.filter(atrasos__in=atrasos).distinct()

    # Preparar datos para el reporte
    reporte_data = []
    for estudiante in estudiantes:
        atrasos_estudiante = atrasos.filter(estudiante=estudiante)
        reporte_data.append({
            'estudiante': estudiante,
            'total_atrasos': atrasos_estudiante.count(),
            'atrasos': atrasos_estudiante
        })

    # Obtener cursos para el filtro
    cursos = []
    if colegio:
        cursos = Estudiante.objects.filter(
            colegio=colegio).values_list('curso', flat=True).distinct()
    else:
        cursos = Estudiante.objects.values_list('curso', flat=True).distinct()

    # Obtener estudiantes para el filtro
    estudiantes_filtro = []
    if colegio:
        estudiantes_filtro = Estudiante.objects.filter(colegio=colegio)
    else:
        estudiantes_filtro = Estudiante.objects.all()

    context = {
        'reporte_data': reporte_data,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'curso_seleccionado': curso,
        'estudiante_seleccionado': estudiante_id,
        'cursos': cursos,
        'estudiantes': estudiantes_filtro,
        'colegio': colegio,
    }

    return render(request, 'registro/reporte_atrasos_por_estudiante.html', context)


@login_required
def reporte_atrasos_por_curso(request):
    colegio = get_colegio_from_user(request.user)

    # Obtener parámetros de filtrado
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')

    # Consulta base
    if colegio:
        atrasos = Atraso.objects.filter(estudiante__colegio=colegio)
    else:
        atrasos = Atraso.objects.all()

    # Aplicar filtros
    if fecha_inicio:
        atrasos = atrasos.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        atrasos = atrasos.filter(fecha__lte=fecha_fin)

    # Obtener cursos
    cursos = atrasos.values('estudiante__curso').annotate(
        total=Count('id')).order_by('estudiante__curso')

    # Preparar datos para el reporte
    reporte_data = []
    for curso_data in cursos:
        curso = curso_data['estudiante__curso']
        atrasos_curso = atrasos.filter(estudiante__curso=curso)

        # Obtener detalles de cada atraso
        detalles_atrasos = atrasos_curso.select_related('estudiante').values(
            'estudiante__nombre', 'estudiante__rut', 'fecha', 'hora', 'motivo'
        )

        reporte_data.append({
            'curso': curso,
            'total_atrasos': curso_data['total'],
            'atrasos': detalles_atrasos
        })

    context = {
        'reporte_data': reporte_data,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'colegio': colegio,
    }

    return render(request, 'registro/reporte_atrasos_por_curso.html', context)


@login_required
def reporte_atrasos_por_fecha(request):
    colegio = get_colegio_from_user(request.user)

    # Obtener parámetros de filtrado
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')

    # Consulta base
    if colegio:
        atrasos = Atraso.objects.filter(estudiante__colegio=colegio)
    else:
        atrasos = Atraso.objects.all()

    # Aplicar filtros
    if fecha_inicio:
        atrasos = atrasos.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        atrasos = atrasos.filter(fecha__lte=fecha_fin)

    # Agrupar por fecha
    fechas = atrasos.values('fecha').annotate(
        total=Count('id')).order_by('fecha')

    # Preparar datos para el reporte
    reporte_data = []
    for fecha_data in fechas:
        fecha = fecha_data['fecha']
        atrasos_fecha = atrasos.filter(fecha=fecha)

        # Obtener detalles de cada atraso
        detalles_atrasos = atrasos_fecha.select_related('estudiante').values(
            'estudiante__nombre', 'estudiante__rut', 'estudiante__curso', 'hora', 'motivo'
        )

        reporte_data.append({
            'fecha': fecha,
            'total_atrasos': fecha_data['total'],
            'atrasos': detalles_atrasos
        })

    context = {
        'reporte_data': reporte_data,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'colegio': colegio,
    }

    return render(request, 'registro/reporte_atrasos_por_fecha.html', context)


@login_required
def exportar_reporte_excel(request, tipo_reporte):
    """
    Exporta un reporte a formato Excel.
    """
    colegio = get_colegio_from_user(request.user)

    # Obtener parámetros de filtrado
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    curso = request.GET.get('curso', '')
    estudiante_id = request.GET.get('estudiante', '')

    # Crear un DataFrame de pandas
    if tipo_reporte == 'estudiante':
        # Consulta base
        if colegio:
            atrasos = Atraso.objects.filter(estudiante__colegio=colegio)
        else:
            atrasos = Atraso.objects.all()

        # Aplicar filtros
        if fecha_inicio:
            atrasos = atrasos.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            atrasos = atrasos.filter(fecha__lte=fecha_fin)
        if curso:
            atrasos = atrasos.filter(curso=curso)
        if estudiante_id:
            atrasos = atrasos.filter(estudiante_id=estudiante_id)

        # Preparar datos para el Excel
        data = []
        for atraso in atrasos:
            data.append({
                'Estudiante': atraso.estudiante.nombre,
                'RUT': atraso.estudiante.rut,
                'Curso': atraso.curso,
                'Fecha': atraso.fecha,
                'Hora': atraso.hora,
                'Motivo': atraso.motivo,
                'Registrado por': atraso.registrado_por.username if atraso.registrado_por else 'N/A'
            })

        df = pd.DataFrame(data)
        filename = f'reporte_atrasos_por_estudiante_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

    elif tipo_reporte == 'curso':
        # Consulta base
        if colegio:
            atrasos = Atraso.objects.filter(estudiante__colegio=colegio)
        else:
            atrasos = Atraso.objects.all()

        # Aplicar filtros
        if fecha_inicio:
            atrasos = atrasos.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            atrasos = atrasos.filter(fecha__lte=fecha_fin)

        # Obtener cursos
        cursos = []
        if colegio:
            cursos = Estudiante.objects.filter(
                colegio=colegio).values_list('curso', flat=True).distinct()
        else:
            cursos = Estudiante.objects.values_list(
                'curso', flat=True).distinct()

        # Preparar datos para el Excel
        data = []
        for curso_nombre in cursos:
            atrasos_curso = atrasos.filter(curso=curso_nombre)
            estudiantes_curso = Estudiante.objects.filter(curso=curso_nombre)
            if colegio:
                estudiantes_curso = estudiantes_curso.filter(colegio=colegio)

            # Calcular estadísticas
            total_estudiantes = estudiantes_curso.count()
            total_atrasos = atrasos_curso.count()
            estudiantes_con_atrasos = estudiantes_curso.filter(
                atrasos__in=atrasos_curso).distinct().count()

            # Calcular porcentaje de estudiantes con atrasos
            porcentaje = 0
            if total_estudiantes > 0:
                porcentaje = (estudiantes_con_atrasos /
                              total_estudiantes) * 100

            data.append({
                'Curso': curso_nombre,
                'Total Estudiantes': total_estudiantes,
                'Total Atrasos': total_atrasos,
                'Estudiantes con Atrasos': estudiantes_con_atrasos,
                'Porcentaje': round(porcentaje, 2)
            })

        df = pd.DataFrame(data)
        filename = f'reporte_atrasos_por_curso_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

    elif tipo_reporte == 'fecha':
        # Consulta base
        if colegio:
            atrasos = Atraso.objects.filter(estudiante__colegio=colegio)
        else:
            atrasos = Atraso.objects.all()

        # Aplicar filtros
        if fecha_inicio:
            atrasos = atrasos.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            atrasos = atrasos.filter(fecha__lte=fecha_fin)

        # Agrupar por fecha
        fechas = atrasos.values('fecha').annotate(
            total=Count('id')).order_by('fecha')

        # Preparar datos para el Excel
        data = []
        for fecha_data in fechas:
            fecha = fecha_data['fecha']
            atrasos_fecha = atrasos.filter(fecha=fecha)

            # Agrupar por curso
            cursos = atrasos_fecha.values('curso').annotate(
                total=Count('id')).order_by('curso')

            for curso_data in cursos:
                data.append({
                    'Fecha': fecha,
                    'Curso': curso_data['curso'],
                    'Total Atrasos': curso_data['total']
                })

        df = pd.DataFrame(data)
        filename = f'reporte_atrasos_por_fecha_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

    else:
        return HttpResponse("Tipo de reporte no válido", status=400)

    # Crear el archivo Excel
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Escribir el DataFrame a un archivo Excel
    df.to_excel(response, index=False)

    return response


@login_required
def dashboard(request):
    colegio = get_colegio_from_user(request.user)

    # Obtener estadísticas generales
    if colegio:
        total_estudiantes = Estudiante.objects.filter(colegio=colegio).count()
        total_atrasos = Atraso.objects.filter(
            estudiante__colegio=colegio).count()
    else:
        total_estudiantes = Estudiante.objects.count()
        total_atrasos = Atraso.objects.count()

    # Datos para el gráfico de atrasos por fecha
    atrasos_por_fecha = Atraso.objects.filter(estudiante__colegio=colegio).values(
        'fecha').annotate(total=Count('id')).order_by('fecha')

    # Cursos con más atrasos
    cursos_con_mas_atrasos = Atraso.objects.filter(estudiante__colegio=colegio).values(
        'estudiante__curso').annotate(total=Count('id')).order_by('-total')[:5]

    # Fecha con más atrasos
    fecha_con_mas_atrasos = atrasos_por_fecha.order_by('-total').first()

    # Estudiantes con más atrasos globales
    estudiantes_con_mas_atrasos_globales = Atraso.objects.filter(estudiante__colegio=colegio).values(
        'estudiante__nombre').annotate(total=Count('id')).order_by('-total')[:5]

    # Estudiantes con más atrasos semanales
    last_week = timezone.now() - timedelta(days=7)
    estudiantes_con_mas_atrasos_semanales = Atraso.objects.filter(estudiante__colegio=colegio, fecha__gte=last_week).values(
        'estudiante__nombre').annotate(total=Count('id')).order_by('-total')[:5]

    # Estudiantes con más atrasos mensuales
    last_month = timezone.now() - timedelta(days=30)
    estudiantes_con_mas_atrasos_mensuales = Atraso.objects.filter(estudiante__colegio=colegio, fecha__gte=last_month).values(
        'estudiante__nombre').annotate(total=Count('id')).order_by('-total')[:5]

    context = {
        'total_estudiantes': total_estudiantes,
        'total_atrasos': total_atrasos,
        'fechas': [item['fecha'].strftime("%d/%m/%Y") for item in atrasos_por_fecha],
        'atrasos': [item['total'] for item in atrasos_por_fecha],
        'cursos_con_mas_atrasos': cursos_con_mas_atrasos,
        'fecha_con_mas_atrasos': fecha_con_mas_atrasos,
        'estudiantes_con_mas_atrasos_globales': estudiantes_con_mas_atrasos_globales,
        'estudiantes_con_mas_atrasos_semanales': estudiantes_con_mas_atrasos_semanales,
        'estudiantes_con_mas_atrasos_mensuales': estudiantes_con_mas_atrasos_mensuales,
    }

    return render(request, 'registro/dashboard.html', context)
