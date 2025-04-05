from datetime import datetime
import json
import logging
import pandas as pd

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth import login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test

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
    # Obtener el colegio del usuario
    colegio = get_colegio_from_user(request.user)

    if request.method == 'POST':
        form = AtrasoForm(request.POST, colegio=colegio)
        if form.is_valid():
            atraso = form.save(commit=False)
            atraso.registrado_por = request.user
            # Asegurarse de que la hora esté establecida
            if not atraso.hora:
                atraso.hora = timezone.now().time()
            atraso.save()
            messages.success(request, 'Atraso registrado exitosamente.')
            return redirect('lista_atrasos')
    else:
        form = AtrasoForm(colegio=colegio)

    return render(request, 'registro/atraso_form.html', {'form': form})


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


@login_required
def buscar_estudiantes(request):
    try:
        # Obtener el colegio del usuario
        colegio = get_colegio_from_user(request.user)

        # Iniciar con todos los estudiantes
        estudiantes = Estudiante.objects.all()

        # Filtrar por colegio si existe
        if colegio:
            estudiantes = estudiantes.filter(colegio=colegio)

        # Obtener el término de búsqueda
        query = request.GET.get('q', '').strip()

        if query:
            # Filtrar por nombre o RUT
            estudiantes = estudiantes.filter(
                Q(nombre__icontains=query) |
                Q(rut__icontains=query)
            )

            # Preparar los resultados
            resultados = [{
                'id': estudiante.id,
                'nombre': estudiante.nombre,
                'rut': estudiante.rut,
                'curso': estudiante.curso
            } for estudiante in estudiantes]
        else:
            resultados = []

        return JsonResponse(resultados, safe=False)

    except Exception as e:
        logger.error(f"Error en buscar_estudiantes: {str(e)}")
        return JsonResponse({
            'error': 'Error al buscar estudiantes',
            'detail': str(e)
        }, status=500)


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
