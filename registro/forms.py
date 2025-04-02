from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Estudiante, Atraso, Colegio, PerfilUsuario
from django.utils import timezone


class ColegioForm(forms.ModelForm):
    class Meta:
        model = Colegio
        fields = ['nombre', 'rut', 'direccion', 'telefono', 'email']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'rut': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class RegistroUsuarioForm(UserCreationForm):
    email = forms.EmailField(required=True)
    cargo = forms.CharField(max_length=100)
    colegio = forms.ModelChoiceField(
        queryset=Colegio.objects.filter(activo=True))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1',
                  'password2', 'cargo', 'colegio']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            PerfilUsuario.objects.create(
                usuario=user,
                colegio=self.cleaned_data['colegio'],
                cargo=self.cleaned_data['cargo']
            )
        return user


class EstudianteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and not user.is_superuser:
            # Si es un usuario normal, el campo colegio será de solo lectura
            perfil = user.perfilusuario
            self.fields['colegio'].widget = forms.HiddenInput()
            self.fields['colegio'].initial = perfil.colegio.id
            self.instance.colegio = perfil.colegio
        else:
            # Si es superusuario, puede seleccionar el colegio
            self.fields['colegio'].widget.attrs['class'] = 'form-control'

    class Meta:
        model = Estudiante
        fields = ['colegio', 'rut', 'nombre', 'curso',
                  'email_principal', 'email_secundario']
        widgets = {
            'rut': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '12345678-9',
                'pattern': '^[0-9]{7,8}-[0-9kK]{1}$',
                'title': 'Ingrese el RUT sin puntos y con guión (Ejemplo: 12345678-9)'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo del estudiante'
            }),
            'curso': forms.Select(attrs={
                'class': 'form-control'
            }),
            'email_principal': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'email_secundario': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo.secundario@ejemplo.com'
            })
        }
        help_texts = {
            'rut': 'Ingrese el RUT sin puntos y con guión (Ejemplo: 12345678-9)',
            'email_secundario': 'Campo opcional'
        }


class AtrasoForm(forms.ModelForm):
    class Meta:
        model = Atraso
        fields = ['estudiante', 'fecha', 'hora', 'curso', 'motivo']
        widgets = {
            'estudiante': forms.Select(attrs={'class': 'form-control'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hora': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'curso': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        colegio = kwargs.pop('colegio', None)
        super().__init__(*args, **kwargs)
        if colegio:
            self.fields['estudiante'].queryset = Estudiante.objects.filter(
                colegio=colegio)

        # Establecer la fecha actual por defecto
        self.fields['fecha'].initial = timezone.now().date()
        # Establecer la hora actual por defecto
        self.fields['hora'].initial = timezone.now().time()

    def clean_estudiante(self):
        estudiante = self.cleaned_data.get('estudiante')
        if estudiante:
            # Establecer el curso del estudiante automáticamente
            self.cleaned_data['curso'] = estudiante.curso
        return estudiante

    def clean_estudiante_id(self):
        # Asegurarse de que el ID del estudiante es válido
        estudiante_id = self.cleaned_data.get('estudiante')
        if estudiante_id:
            try:
                estudiante = Estudiante.objects.get(id=estudiante_id)
                return estudiante
            except Estudiante.DoesNotExist:
                raise forms.ValidationError("Estudiante no encontrado.")
        raise forms.ValidationError("Debe seleccionar un estudiante.")
